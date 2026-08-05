"""Explicit intake-to-artifact workflow for the research network."""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from datetime import datetime, timezone
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
    BranchStatus,
    FinalResearchPackage,
    ManagerName,
    RunMetrics,
    SpecialistFinding,
    UserResearchRequest,
)
from ..reporting.render import persist_package
from ..telemetry.metrics import EventRecorder, Stopwatch, finish_metrics
from ..tools.research import FixtureResearchBackend, LiveResearchBackend
from ..tools.source_store import SourceLedger, validate_claim_references, validate_report


class WorkflowError(RuntimeError):
    """Raised when deterministic workflow guards reject a run."""


class ResearchWorkflow:
    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or AppConfig()
        self.graph = build_agent_graph(self.config)

    async def run(self, request: UserResearchRequest, answers: dict[str, str] | None = None) -> FinalResearchPackage:
        decision = assess_request(request)
        if not decision.allowed:
            raise WorkflowError("Request rejected by guardrails: " + "; ".join(decision.reasons))

        run_id = f"run-{uuid.uuid4().hex[:12]}"
        trace_id = f"trace_{uuid.uuid4().hex}"
        context = RunContext(config=self.config, run_id=run_id, trace_id=trace_id)
        events = EventRecorder(run_id)
        stopwatch = Stopwatch()
        started_at = datetime.now(timezone.utc)
        events.record("run_started", provider=self.config.research_provider)

        brief = build_brief(request, answers)
        plan = build_plan(brief)
        events.record("plan_created", branches=[branch.value for branch in plan.selected_branches])
        backend = FixtureResearchBackend(self.config.fixture_path) if self.config.research_provider == "offline" else LiveResearchBackend(self.config.max_sources)

        findings = await self._run_specialists(plan.assignments, backend, context, events)
        ledger = SourceLedger()
        for finding in findings:
            for source in finding.discovered_sources:
                ledger.add(source)
        claim_validation = validate_claim_references([claim for finding in findings for claim in finding.claims], ledger)
        context.validation_failures.extend(claim_validation.errors)
        events.record("branches_validated", errors=len(claim_validation.errors), warnings=len(claim_validation.warnings))

        grouped: dict[ManagerName, list[SpecialistFinding]] = defaultdict(list)
        for finding in findings:
            for manager, branch_names in {
                ManagerName.POLICY: {"government_sources", "legal_regulatory", "think_tank_academic"},
                ManagerName.INDUSTRY: {"consumer", "loan_originator", "servicing", "secondary_market_risk_transfer"},
                ManagerName.ADVOCACY: {"general_consumer_advocacy", "disadvantaged_communities", "financial_sustainability"},
                ManagerName.GLOBAL: {"global_research"},
            }.items():
                if finding.branch.value in branch_names:
                    grouped[manager].append(finding)
        manager_syntheses = await asyncio.gather(*[
            reconcile_manager(manager, manager_findings, context)
            for manager, manager_findings in grouped.items()
        ])
        events.record("managers_reconciled", count=len(manager_syntheses))

        draft = await write_report(brief, list(manager_syntheses), ledger.ids(), context)
        pre_review = validate_report(draft, ledger)
        context.validation_failures.extend(pre_review.errors)
        events.record("pre_review_validation", errors=len(pre_review.errors), warnings=len(pre_review.warnings))
        review = await review_report(draft, ledger, [item.model_dump(mode="json") for item in manager_syntheses], context)
        final_report = draft
        if review.release_recommendation.value == "revise" or any(item.mandatory_revision for item in review.findings):
            final_report = await revise_report(draft, review, context)
            events.record("bounded_revision", revision_count=final_report.revision_count)
        final_validation = validate_report(final_report, ledger)
        context.validation_failures.extend(final_validation.errors)
        events.record("final_validation", errors=len(final_validation.errors), warnings=len(final_validation.warnings))

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
        (artifact_dir / "events.json").write_text(__import__("json").dumps(events.events, indent=2), encoding="utf-8")
        events.record("artifacts_persisted", path=str(artifact_dir))
        return package

    async def _run_specialists(self, assignments: list, backend: object, context: RunContext, events: EventRecorder) -> list[SpecialistFinding]:
        semaphore = asyncio.Semaphore(self.config.max_concurrency)

        async def run_one(assignment: object) -> SpecialistFinding:
            async with semaphore:
                events.record("branch_started", branch=assignment.branch.value)
                attempts = 0
                finding: SpecialistFinding | None = None
                while attempts <= self.config.max_branch_retries:
                    attempts += 1
                    finding = await run_specialist(assignment, backend, context)
                    if finding.status != BranchStatus.FAILED:
                        break
                if attempts > 1:
                    context.retries[assignment.branch.value] = attempts - 1
                assert finding is not None
                events.record("branch_finished", branch=assignment.branch.value, status=finding.status.value, attempts=attempts)
                return finding

        return list(await asyncio.gather(*(run_one(assignment) for assignment in assignments)))
