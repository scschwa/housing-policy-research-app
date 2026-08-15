import asyncio

import pytest

import housing_policy_agents.agents.writer as writer_module
from housing_policy_agents.agents.managers import reconcile_manager
from housing_policy_agents.agents.reviewer import review_report
from housing_policy_agents.agents.writer import revise_report, write_report
from housing_policy_agents.config import AppConfig
from housing_policy_agents.context import RunContext
from housing_policy_agents.models import (
    BranchName,
    BranchStatus,
    ManagerName,
    ManagerSynthesis,
    ResearchBrief,
    RunMode,
    SpecialistFinding,
)
from housing_policy_agents.tools.source_store import SourceLedger, validate_report


def live_test_context() -> RunContext:
    return RunContext(
        config=AppConfig(
            research_provider="web",
            allow_network=True,
            openai_api_key="test-only",
        ),
        run_id="run-test-containment",
        trace_id="trace-test-containment",
    )


def test_manager_stops_synthesis_when_all_findings_lack_validated_sources() -> None:
    finding = SpecialistFinding(
        branch=BranchName.LEGAL,
        agent_name="legal_regulatory_researcher",
        status=BranchStatus.FAILED,
        summary="The branch failed validation.",
        error="ModelBehaviorError",
    )

    synthesis = asyncio.run(
        reconcile_manager(
            ManagerName.POLICY,
            [finding],
            live_test_context(),
        )
    )

    assert synthesis.status == BranchStatus.PARTIAL
    assert synthesis.reconciled_claims == []
    assert synthesis.limitations


def test_empty_evidence_run_uses_safe_report_and_skips_live_downstream_calls() -> None:
    brief = ResearchBrief(
        request_id="req-test-containment",
        question="What are the possible consequences of this housing policy?",
        audience="policy analyst",
        jurisdiction="United States",
        policy_scope="housing finance",
        time_horizon="near term and long term",
        stakeholder_perspective="balanced",
        mode=RunMode.FAST,
    )
    manager = reconcile_manager
    finding = SpecialistFinding(
        branch=BranchName.GOVERNMENT,
        agent_name="government_sources_researcher",
        status=BranchStatus.FAILED,
        summary="No validated result.",
        error="ModelBehaviorError",
    )
    synthesis = asyncio.run(manager(ManagerName.POLICY, [finding], live_test_context()))
    report = asyncio.run(
        write_report(brief, [synthesis], SourceLedger().ids(), live_test_context())
    )
    ledger = SourceLedger()
    validation = validate_report(report, ledger)
    review = asyncio.run(review_report(report, ledger, [], live_test_context()))
    revised = asyncio.run(revise_report(report, review, live_test_context()))

    assert validation.errors == []
    assert report.source_ids_used == []
    assert review.findings == []
    assert revised.revised is True
    assert revised.revision_count == 1


def test_writer_model_failure_is_contained_after_specialist_evidence_arrives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    brief = ResearchBrief(
        request_id="req-test-writer-fallback",
        question="What are the possible consequences of this housing policy?",
        audience="policy analyst",
        jurisdiction="United States",
        policy_scope="housing finance",
        time_horizon="near term and long term",
        stakeholder_perspective="balanced",
        mode=RunMode.FAST,
    )
    synthesis = ManagerSynthesis(
        manager=ManagerName.POLICY,
        status=BranchStatus.COMPLETED,
        specialist_branches=[BranchName.GOVERNMENT],
        branch_statuses={BranchName.GOVERNMENT: BranchStatus.COMPLETED},
    )

    async def fail_writer(**_: object) -> object:
        raise RuntimeError("simulated typed-output failure")

    monkeypatch.setattr(writer_module, "build_writer_agent", lambda _: object())
    monkeypatch.setattr(writer_module, "run_agent_with_telemetry", fail_writer)
    context = live_test_context()
    report = asyncio.run(
        write_report(brief, [synthesis], {"s1"}, context)
    )

    assert report.source_ids_used == []
    assert "typed validation" in report.executive_summary
    assert "writer_fallback_reason" in context.metadata
