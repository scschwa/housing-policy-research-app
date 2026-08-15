"""Versioned OpenAI Agents SDK agent definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import AppConfig
from ..models import BranchName, DraftReport, ManagerSynthesis, ResearchPlan, SpecialistFinding
from .orchestrator import BRANCH_PROFILES

PROMPT_ROOT = Path(__file__).parents[1] / "prompts"

MANAGER_ROLE_GUIDANCE = {
    "policy_research_manager": (
        "You are the calm, skeptical policy integrator for government, legal, and academic evidence. "
        "Reconcile authority, policy baseline, empirical mechanisms, and uncertainty without allowing "
        "a compelling narrative to outrun the record."
    ),
    "industry_research_manager": (
        "You are an operations-minded market integrator. Compare consumer, origination, servicing, and "
        "risk-transfer findings while separating observed practice, stakeholder incentives, and forecasts."
    ),
    "advocacy_research_manager": (
        "You are an equity-conscious but evidence-disciplined integrator. Preserve consumer and community "
        "concerns, identify who bears risk, and distinguish advocacy positions from measured outcomes."
    ),
    "global_research_manager": (
        "You are a comparative-policy analyst. Admit institutional differences, reject superficial country "
        "analogies, and retain only lessons that can be translated into conditional U.S. design questions."
    ),
}


def read_prompt(name: str) -> str:
    return (PROMPT_ROOT / f"{name}.md").read_text(encoding="utf-8")


def agent_output_schema(output_type: type[Any]) -> Any:
    """Prefer strict schemas, relaxing only models with SDK-incompatible mappings.

    The Agents SDK strict-schema normalizer rejects JSON Schema objects whose
    ``additionalProperties`` value is itself a schema. Pydantic models such as
    ``ManagerSynthesis.branch_statuses`` and ``DecisionMatrix.scores`` use typed
    mappings for valid internal data, so those outputs need the SDK's explicit
    non-strict fallback. Pydantic validation still runs on the returned object.
    """

    from agents import AgentOutputSchema, UserError

    try:
        return AgentOutputSchema(output_type, strict_json_schema=True)
    except UserError:
        return AgentOutputSchema(output_type, strict_json_schema=False)


def build_orchestrator_agent(config: AppConfig) -> Any:
    from agents import Agent

    return Agent(
        name="Research Orchestrator",
        instructions=read_prompt("orchestrator"),
        model=config.openai_model,
        output_type=agent_output_schema(ResearchPlan),
    )


def build_specialist_agent(branch: str, config: AppConfig, tools: list[Any]) -> Any:
    from agents import Agent

    profile = BRANCH_PROFILES[BranchName(branch)]
    profile_text = "\n".join(
        [
            f"Branch role: {profile.role}",
            f"Role definition: {profile.role_definition}",
            "In scope: " + "; ".join(profile.in_scope),
            "Out of scope: " + "; ".join(profile.out_of_scope),
            "Preferred sources: " + "; ".join(profile.preferred_sources),
            "Research dimensions: " + "; ".join(profile.research_dimensions),
        ]
    )
    return Agent(
        name=f"{branch.replace('_', ' ').title()} Researcher",
        instructions=(
            f"{read_prompt('specialist')}\n\n{profile_text}\n\n"
            f"Your assigned branch is {branch}. Follow the runtime assignment context exactly."
        ),
        model=config.openai_model,
        tools=tools,
        output_type=agent_output_schema(SpecialistFinding),
    )


def build_manager_agent(
    manager: str, config: AppConfig, specialist_tools: list[Any] | None = None
) -> Any:
    from agents import Agent

    return Agent(
        name=manager.replace("_", " ").title(),
        instructions=(
            f"{read_prompt('manager')}\n\n"
            f"Manager persona: {MANAGER_ROLE_GUIDANCE.get(manager, 'You are a careful evidence integrator.')}"
        ),
        model=config.openai_model,
        tools=specialist_tools or [],
        output_type=agent_output_schema(ManagerSynthesis),
    )


def build_writer_agent(config: AppConfig) -> Any:
    from agents import Agent

    return Agent(
        name="Synthesis Writer",
        instructions=read_prompt("writer"),
        model=config.openai_model,
        output_type=agent_output_schema(DraftReport),
    )


def build_reviewer_agent(config: AppConfig) -> Any:
    from agents import Agent

    from ..models import AdversarialReview

    return Agent(
        name="Adversarial Reviewer",
        instructions=read_prompt("reviewer"),
        model=config.openai_model,
        output_type=agent_output_schema(AdversarialReview),
    )


def build_rework_agent(config: AppConfig) -> Any:
    from agents import Agent

    return Agent(
        name="Validation Re-work Specialist",
        instructions=read_prompt("rework"),
        model=config.openai_model,
        output_type=agent_output_schema(DraftReport),
    )


def build_agent_graph(config: AppConfig) -> dict[str, Any]:
    """Build the configured graph and expose manager agents as callable tools."""

    specialists: dict[str, Any] = {}
    for branch in (
        "government_sources",
        "legal_regulatory",
        "think_tank_academic",
        "consumer",
        "loan_originator",
        "servicing",
        "secondary_market_risk_transfer",
        "general_consumer_advocacy",
        "disadvantaged_communities",
        "financial_sustainability",
        "global_research",
    ):
        specialists[branch] = build_specialist_agent(branch, config, [])

    managers: dict[str, Any] = {}
    for manager, branches in {
        "policy_research_manager": [
            "government_sources",
            "legal_regulatory",
            "think_tank_academic",
        ],
        "industry_research_manager": [
            "consumer",
            "loan_originator",
            "servicing",
            "secondary_market_risk_transfer",
        ],
        "advocacy_research_manager": [
            "general_consumer_advocacy",
            "disadvantaged_communities",
            "financial_sustainability",
        ],
        "global_research_manager": ["global_research"],
    }.items():
        tools = [
            specialists[branch].as_tool(
                tool_name=f"research_{branch}",
                tool_description=(
                    f"Invoke the bounded {BRANCH_PROFILES[BranchName(branch)].role}. "
                    "Pass a complete bounded request containing the policy question, manager request, "
                    "policy decisions supported, branch objective, scope boundaries, preferred source "
                    "types, research dimensions, sibling context, and required response contract. "
                    "The specialist returns claim-level typed evidence using short source IDs and URLs "
                    "only in source.url; do not ask it for a general narrative."
                ),
                max_turns=config.max_turns_per_agent,
            )
            for branch in branches
        ]
        managers[manager] = build_manager_agent(manager, config, tools)

    orchestrator = build_orchestrator_agent(config)
    manager_tools = [
        managers[name].as_tool(
            tool_name=f"run_{name}",
            tool_description=f"Run and reconcile the {name} branch.",
            max_turns=config.max_turns_per_agent,
        )
        for name in managers
    ]
    return {
        "orchestrator": orchestrator,
        "managers": managers,
        "manager_tools": manager_tools,
        "specialists": specialists,
        "writer": build_writer_agent(config),
        "reviewer": build_reviewer_agent(config),
        "rework": build_rework_agent(config),
    }


def mermaid_graph() -> str:
    return """flowchart TD
    O[Research Orchestrator] --> PM[Policy Research Manager]
    O --> IM[Industry Research Manager]
    O --> AM[Advocacy Research Manager]
    O --> GM[Global Research Manager]
    PM --> G[Government Sources]
    PM --> L[Legal and Regulatory]
    PM --> A[Think Tank and Academic]
    IM --> C[Consumer]
    IM --> LO[Loan Originator]
    IM --> S[Servicing]
    IM --> R[Secondary Market and Risk Transfer]
    AM --> GA[General Consumer Advocacy]
    AM --> DC[Disadvantaged Communities]
    AM --> FS[Financial Sustainability]
    GM --> GL[Global Research]
    G --> W[Synthesis Writer]
    L --> W
    A --> W
    C --> W
    LO --> W
    S --> W
    R --> W
    GA --> W
    DC --> W
    FS --> W
    GL --> W
    W --> V[Deterministic Validation]
    V --> RW[Validation Re-work]
    RW --> AR[Adversarial Review]
    AR --> RV[One Bounded Revision]
    RV --> FV[Final Validation and Re-work]
    FV --> OUT[Final Research Package and Audit]"""
