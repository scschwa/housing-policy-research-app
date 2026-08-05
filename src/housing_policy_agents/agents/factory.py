"""Versioned OpenAI Agents SDK agent definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import AppConfig
from ..models import DraftReport, ManagerSynthesis, ResearchPlan, SpecialistFinding

PROMPT_ROOT = Path(__file__).parents[1] / "prompts"


def read_prompt(name: str) -> str:
    return (PROMPT_ROOT / f"{name}.md").read_text(encoding="utf-8")


def build_orchestrator_agent(config: AppConfig) -> Any:
    from agents import Agent

    return Agent(
        name="Research Orchestrator",
        instructions=read_prompt("orchestrator"),
        model=config.openai_model,
        output_type=ResearchPlan,
    )


def build_specialist_agent(branch: str, config: AppConfig, tools: list[Any]) -> Any:
    from agents import Agent

    return Agent(
        name=f"{branch.replace('_', ' ').title()} Researcher",
        instructions=f"{read_prompt('specialist')}\nYour assigned branch is {branch}.",
        model=config.openai_model,
        tools=tools,
        output_type=SpecialistFinding,
    )


def build_manager_agent(
    manager: str, config: AppConfig, specialist_tools: list[Any] | None = None
) -> Any:
    from agents import Agent

    return Agent(
        name=manager.replace("_", " ").title(),
        instructions=(
            "You reconcile bounded specialist findings. Preserve disagreements and label incentive-driven claims. "
            "Do not invent sources or legal conclusions. Return the typed manager synthesis."
        ),
        model=config.openai_model,
        tools=specialist_tools or [],
        output_type=ManagerSynthesis,
    )


def build_writer_agent(config: AppConfig) -> Any:
    from agents import Agent

    return Agent(
        name="Synthesis Writer",
        instructions=read_prompt("writer"),
        model=config.openai_model,
        output_type=DraftReport,
    )


def build_reviewer_agent(config: AppConfig) -> Any:
    from agents import Agent

    from ..models import AdversarialReview

    return Agent(
        name="Adversarial Reviewer",
        instructions=read_prompt("reviewer"),
        model=config.openai_model,
        output_type=AdversarialReview,
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
                tool_description=f"Run the bounded {branch} specialist.",
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
    V --> AR[Adversarial Review]
    AR --> RV[One Bounded Revision]
    RV --> OUT[Final Research Package]"""
