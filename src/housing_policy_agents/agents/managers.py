"""Manager-level reconciliation of specialist findings."""

from __future__ import annotations

import json

from ..context import RunContext
from ..models import (
    BranchStatus,
    ManagerName,
    ManagerSynthesis,
    ResearchBrief,
    SpecialistFinding,
)
from ..telemetry.interactions import run_agent_with_telemetry
from .factory import build_manager_agent

MANAGER_BRANCHES = {
    ManagerName.POLICY: {"government_sources", "legal_regulatory", "think_tank_academic"},
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
}


async def reconcile_manager(
    manager: ManagerName,
    findings: list[SpecialistFinding],
    context: RunContext,
    brief: ResearchBrief | None = None,
) -> ManagerSynthesis:
    branches = [finding.branch for finding in findings]
    statuses = {finding.branch: finding.status for finding in findings}
    overall = (
        BranchStatus.COMPLETED
        if all(status == BranchStatus.COMPLETED for status in statuses.values())
        else BranchStatus.PARTIAL
    )
    usable_findings = [
        finding
        for finding in findings
        if finding.status == BranchStatus.COMPLETED and finding.discovered_sources
    ]
    if not usable_findings:
        failed_branches = [
            finding.branch.value
            for finding in findings
            if finding.status != BranchStatus.COMPLETED
        ]
        return ManagerSynthesis(
            manager=manager,
            status=BranchStatus.PARTIAL,
            specialist_branches=branches,
            branch_statuses=statuses,
            findings=findings,
            limitations=[
                "No specialist branch returned a validated finding with a discovered source.",
                "This manager must not infer substantive conclusions or invent citation IDs.",
                f"Unavailable branches: {', '.join(failed_branches) or 'none reported'}.",
            ],
        )
    if context.config.research_provider == "offline":
        claims = [claim for finding in findings for claim in finding.claims]
        contradictions = [item for finding in findings for item in finding.contradictions]
        agreements = [
            finding.summary for finding in findings if finding.status == BranchStatus.COMPLETED
        ]
        disagreements = [item.description for item in contradictions]
        incentive = []
        if manager == ManagerName.INDUSTRY:
            incentive = [
                "Industry claims about operational burden and risk allocation may reflect genuine constraints as well as stakeholder incentives.",
            ]
        limitations = sorted({item for finding in findings for item in finding.limitations})
        return ManagerSynthesis(
            manager=manager,
            status=overall,
            specialist_branches=branches,
            branch_statuses=statuses,
            findings=findings,
            country_comparisons=[
                comparison
                for finding in findings
                for comparison in finding.country_comparisons
            ],
            reconciled_claims=claims,
            contradictions=contradictions,
            agreements=agreements,
            disagreements=disagreements,
            incentive_driven_claims=incentive,
            limitations=limitations,
        )

    from agents import RunConfig

    agent = build_manager_agent(manager.value, context.config)
    input_payload = {
        "manager": manager.value,
        "handoff_context": {
            "upstream": "bounded specialist findings from the selected branches",
            "downstream": "a synthesis writer producing a decision-ready report",
            "research_question": brief.question if brief else None,
            "jurisdiction": brief.jurisdiction if brief else None,
            "policy_scope": brief.policy_scope if brief else None,
            "time_horizon": brief.time_horizon if brief else None,
            "manager_request": (
                "Reconcile what the supplied findings establish, what they only suggest, "
                "where they disagree, which claims are source-supported, and what evidence "
                "gaps or sibling questions must be carried downstream."
            ),
            "source_id_contract": (
                "Use only the short source IDs already present in the findings. Never invent or "
                "substitute URLs for source IDs."
            ),
        },
        "findings": [item.model_dump(mode="json") for item in findings],
    }
    result = await run_agent_with_telemetry(
        context=context,
        agent=agent,
        runner_input=json.dumps(input_payload, indent=2),
        input_payload=input_payload,
        agent_name=manager.value,
        stage="reconciliation",
        max_turns=context.config.max_turns_per_agent,
        run_config=RunConfig(
            model=context.config.openai_model,
            workflow_name="Housing Policy Research Network",
            trace_id=context.trace_id,
            trace_include_sensitive_data=context.config.trace_include_sensitive_data,
            trace_metadata={"run_id": context.run_id, "manager": manager.value},
        ),
    )
    synthesis = result.final_output
    if not isinstance(synthesis, ManagerSynthesis):
        raise TypeError("manager did not return ManagerSynthesis")
    synthesis.manager = manager
    return synthesis
