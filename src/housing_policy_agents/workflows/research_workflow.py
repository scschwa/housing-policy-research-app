"""Explicit intake-to-artifact workflow for the research network."""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from ..agents.factory import build_agent_graph
from ..agents.managers import reconcile_manager
from ..agents.orchestrator import build_brief, build_plan
from ..agents.reviewer import review_report
from ..agents.specialists import run_specialist
from ..agents.writer import revise_report, write_report
from ..config import AppConfig
from ..context import RunContext
from ..guardrails import assess_request
from ..models import (
    AdversarialReview,
    BranchName,
    BranchStatus,
    FinalResearchPackage,
    ManagerName,
    ManagerSynthesis,
    ReleaseRecommendation,
    ResearchAssignment,
    ResearchPlan,
    RunMetrics,
    SpecialistFinding,
    UserResearchRequest,
)
from ..reporting.render import persist_package
from ..telemetry.interactions import InteractionTelemetry
from ..telemetry.metrics import EventRecorder, ProgressCallback, Stopwatch, finish_metrics
from ..tools.research import FixtureResearchBackend, LiveResearchBackend, ResearchBackend
from ..tools.source_store import (
    SourceLedger,
    validate_claim_references,
    validate_country_comparisons,
    validate_report,
)


class WorkflowError(RuntimeError):
    """Raised when deterministic workflow guards reject a run."""


class ResearchWorkflow:
    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or AppConfig()
        self.graph = build_agent_graph(self.config)

    async def run(
        self,
        request: UserResearchRequest,
        answers: dict[str, str] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> FinalResearchPackage:
        decision = assess_request(request)
        if not decision.allowed:
            raise WorkflowError("Request rejected by guardrails: " + "; ".join(decision.reasons))

        run_id = f"run-{uuid.uuid4().hex[:12]}"
        trace_id = f"trace_{uuid.uuid4().hex}"
        context = RunContext(
            config=self.config,
            run_id=run_id,
            trace_id=trace_id,
            interaction_telemetry=InteractionTelemetry(
                run_id=run_id,
                enabled=self.config.sub_agent_telemetry_enabled,
                include_content=self.config.sub_agent_telemetry_include_content,
                max_chars=self.config.sub_agent_telemetry_max_chars,
            ),
        )
        telemetry = context.interaction_telemetry
        assert telemetry is not None
        events = EventRecorder(run_id, on_record=progress_callback)
        stopwatch = Stopwatch()
        started_at = datetime.now(UTC)
        events.record("run_started", provider=self.config.research_provider)
        events.record("intake_validated", mode=request.mode.value)

        brief = build_brief(
            request,
            answers,
            clarification_enabled=self.config.enable_clarification,
        )
        plan = self._apply_ablation(build_plan(brief))
        events.record("plan_created", branches=[branch.value for branch in plan.selected_branches])
        events.record("research_started", assignments=len(plan.assignments))
        backend = (
            FixtureResearchBackend(self.config.fixture_path)
            if self.config.research_provider == "offline"
            else LiveResearchBackend(
                self.config.max_sources,
                cache_root=Path(self.config.artifacts_dir) / "cache",
            )
        )

        findings = await self._run_specialists(plan.assignments, backend, context, events)
        ledger = SourceLedger()
        for finding in findings:
            for source in finding.discovered_sources:
                ledger.add(source)
        claim_validation = validate_claim_references(
            [claim for finding in findings for claim in finding.claims], ledger
        )
        context.validation_failures.extend(claim_validation.errors)
        comparison_validation = validate_country_comparisons(
            [
                comparison
                for finding in findings
                for comparison in finding.country_comparisons
            ],
            ledger,
        )
        context.validation_failures.extend(comparison_validation.errors)
        events.record(
            "branches_validated",
            errors=len(claim_validation.errors),
            warnings=len(claim_validation.warnings),
            source_count=len(ledger.ids()),
        )
        if not ledger.ids():
            events.record(
                "evidence_unavailable",
                failed_branches=[
                    finding.branch.value
                    for finding in findings
                    if finding.status != BranchStatus.COMPLETED
                ],
                message="No validated specialist source records reached the source ledger.",
            )

        grouped: dict[ManagerName, list[SpecialistFinding]] = defaultdict(list)
        for finding in findings:
            for manager, branch_names in {
                ManagerName.POLICY: {
                    "government_sources",
                    "legal_regulatory",
                    "think_tank_academic",
                },
                ManagerName.INDUSTRY: {
                    "consumer",
                    "loan_originator",
                    "servicing",
                    "secondary_market_risk_transfer",
                },
                ManagerName.ADVOCACY: {
                    "general_consumer_advocacy",
                    "disadvantaged_communities",
                    "financial_sustainability",
                },
                ManagerName.GLOBAL: {"global_research"},
            }.items():
                if finding.branch.value in branch_names:
                    grouped[manager].append(finding)
        if self.config.enable_manager_reconciliation:
            async def reconcile_one(
                manager: ManagerName, manager_findings: list[SpecialistFinding]
            ) -> ManagerSynthesis:
                events.record(
                    "manager_started",
                    manager=manager.value,
                    branches=[item.branch.value for item in manager_findings],
                )
                telemetry.handoff(
                    source="specialist_network",
                    target=manager.value,
                    stage="manager_reconciliation",
                    payload={
                        "branches": [item.branch.value for item in manager_findings],
                        "finding_count": len(manager_findings),
                        "failed_branches": [
                            item.branch.value
                            for item in manager_findings
                            if item.status == BranchStatus.FAILED
                        ],
                        "research_question": brief.question,
                        "policy_scope": brief.policy_scope,
                        "source_id_contract": "short internal IDs; URLs remain in source.url",
                    },
                )
                synthesis = await reconcile_manager(
                    manager,
                    manager_findings,
                    context,
                    brief=brief,
                )
                events.record(
                    "manager_finished",
                    manager=manager.value,
                    status=synthesis.status.value,
                )
                return synthesis

            manager_syntheses = await asyncio.gather(
                *[
                    reconcile_one(manager, manager_findings)
                    for manager, manager_findings in grouped.items()
                ]
            )
        else:
            events.record("manager_reconciliation_skipped")
            manager_syntheses = [
                self._pass_through_manager(manager, manager_findings)
                for manager, manager_findings in grouped.items()
            ]
        events.record("managers_reconciled", count=len(manager_syntheses))

        events.record("draft_started")
        telemetry.handoff(
            source="research_managers",
            target="synthesis_writer",
            stage="drafting",
            payload={
                "manager_count": len(manager_syntheses),
                "source_count": len(ledger.ids()),
                "research_question": brief.question,
                "downstream_instruction": (
                    "Use manager findings as evidence inputs; preserve uncertainty, source IDs, "
                    "contradictions, and branch limitations."
                ),
            },
        )
        draft = await write_report(brief, list(manager_syntheses), ledger.ids(), context)
        events.record("draft_completed", sections=len(draft.sections))
        pre_review = validate_report(draft, ledger)
        context.validation_failures.extend(pre_review.errors)
        events.record(
            "pre_review_validation",
            errors=len(pre_review.errors),
            warnings=len(pre_review.warnings),
        )
        if self.config.enable_adversarial_review:
            events.record("review_started")
            telemetry.handoff(
                source="synthesis_writer",
                target="adversarial_reviewer",
                stage="review",
                payload={
                    "section_count": len(draft.sections),
                    "source_count": len(ledger.ids()),
                    "downstream_instruction": (
                        "Check factual support, source quality, legal calibration, uncertainty, "
                        "distributional coverage, and source-ID integrity."
                    ),
                },
            )
            review = await review_report(
                draft,
                ledger,
                [item.model_dump(mode="json") for item in manager_syntheses],
                context,
            )
            events.record(
                "review_completed",
                recommendation=review.release_recommendation.value,
                findings=len(review.findings),
            )
        else:
            events.record("review_skipped")
            review = AdversarialReview(
                citation_completeness=1.0,
                grounding_score=0.0,
                balance_score=0.0,
                calibration_score=0.0,
                security_score=0.0,
                release_recommendation=ReleaseRecommendation.APPROVE_WITH_CAVEATS,
                reviewer_notes=["Adversarial review disabled by ablation configuration."],
            )
        final_report = draft
        if review.release_recommendation.value == "revise" or any(
            item.mandatory_revision for item in review.findings
        ):
            events.record("revision_started")
            telemetry.handoff(
                source="adversarial_reviewer",
                target="synthesis_writer",
                stage="revision",
                payload={
                    "finding_count": len(review.findings),
                    "downstream_instruction": (
                        "Revise only where the review identifies a material issue; retain valid "
                        "citations and do not invent evidence."
                    ),
                },
            )
            fallback_reason: str | None = None
            try:
                final_report = await asyncio.wait_for(
                    revise_report(draft, review, context),
                    timeout=self.config.revision_timeout_seconds,
                )
            except TimeoutError:
                fallback_reason = (
                    f"timeout after {self.config.revision_timeout_seconds} seconds"
                )
            except Exception as exc:
                fallback_reason = f"{type(exc).__name__} from revision output"
            if fallback_reason is not None:
                final_report = draft
                review = review.model_copy(
                    update={
                        "reviewer_notes": [
                            *review.reviewer_notes,
                            f"The bounded revision failed ({fallback_reason}); the validated draft was retained.",
                        ]
                    }
                )
                events.record(
                    "revision_fallback",
                    reason=fallback_reason,
                )
                events.record("bounded_revision", revision_count=0, fallback=True)
            else:
                events.record("bounded_revision", revision_count=final_report.revision_count)
        final_validation = validate_report(final_report, ledger)
        context.validation_failures.extend(final_validation.errors)
        events.record(
            "final_validation",
            errors=len(final_validation.errors),
            warnings=len(final_validation.warnings),
        )

        branch_statuses = {finding.branch.value: finding.status for finding in findings}
        metrics = RunMetrics(
            run_id=run_id,
            started_at=started_at,
            model=self.config.openai_model if self.config.live_enabled else "fixture-deterministic",
            trace_id=trace_id,
            branch_statuses=branch_statuses,
            retries=context.retries,
            validation_failures=context.validation_failures,
            evaluation_scores={
                "citation_completeness": review.citation_completeness,
                "grounding": review.grounding_score,
                "balance": review.balance_score,
                "calibration": review.calibration_score,
                "security": review.security_score,
            },
        )
        finish_metrics(metrics, stopwatch)
        package = FinalResearchPackage(
            run_id=run_id,
            request=request,
            brief=brief,
            plan=plan,
            specialist_findings=findings,
            manager_syntheses=list(manager_syntheses),
            source_ledger=ledger.values(),
            draft_report=draft,
            adversarial_review=review,
            final_report=final_report,
            metrics=metrics,
        )
        artifact_dir = persist_package(package, Path(self.config.artifacts_dir))
        events.record("artifacts_persisted", path=str(artifact_dir))
        (artifact_dir / "events.json").write_text(
            __import__("json").dumps(events.events, indent=2), encoding="utf-8"
        )
        telemetry.persist(artifact_dir)
        return package

    def _apply_ablation(self, plan: ResearchPlan) -> ResearchPlan:
        disabled = {
            BranchName(value) for value in self.config.disabled_branches
        }
        if not disabled:
            return plan
        assignments = [item for item in plan.assignments if item.branch not in disabled]
        selected = [item for item in plan.selected_branches if item not in disabled]
        rationale = {branch: value for branch, value in plan.branch_rationale.items() if branch in selected}
        return plan.model_copy(
            update={
                "selected_branches": selected,
                "assignments": assignments,
                "branch_rationale": rationale,
            }
        )

    @staticmethod
    def _pass_through_manager(
        manager: ManagerName, findings: list[SpecialistFinding]
    ) -> ManagerSynthesis:
        return ManagerSynthesis(
            manager=manager,
            status=(
                BranchStatus.COMPLETED
                if all(item.status == BranchStatus.COMPLETED for item in findings)
                else BranchStatus.PARTIAL
            ),
            specialist_branches=[item.branch for item in findings],
            branch_statuses={item.branch: item.status for item in findings},
            findings=findings,
            country_comparisons=[
                comparison
                for finding in findings
                for comparison in finding.country_comparisons
            ],
            reconciled_claims=[claim for item in findings for claim in item.claims],
            contradictions=[
                contradiction
                for item in findings
                for contradiction in item.contradictions
            ],
            limitations=[
                limitation
                for item in findings
                for limitation in item.limitations
            ],
        )

    async def _run_specialists(
        self,
        assignments: list[ResearchAssignment],
        backend: ResearchBackend,
        context: RunContext,
        events: EventRecorder,
    ) -> list[SpecialistFinding]:
        semaphore = asyncio.Semaphore(self.config.max_concurrency)

        async def run_one(assignment: ResearchAssignment) -> SpecialistFinding:
            async with semaphore:
                events.record("branch_started", branch=assignment.branch.value)
                attempts = 0
                finding: SpecialistFinding | None = None
                while attempts <= self.config.max_branch_retries:
                    attempts += 1
                    finding = await run_specialist(assignment, backend, context)
                    if isinstance(backend, LiveResearchBackend):
                        for query in assignment.search_queries:
                            backend.cache_results(query, finding.discovered_sources)
                    if finding.status != BranchStatus.FAILED:
                        break
                if attempts > 1:
                    context.retries[assignment.branch.value] = attempts - 1
                assert finding is not None
                events.record(
                    "branch_finished",
                    branch=assignment.branch.value,
                    status=finding.status.value,
                    attempts=attempts,
                )
                return finding

        return list(await asyncio.gather(*(run_one(assignment) for assignment in assignments)))
