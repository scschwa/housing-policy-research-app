from housing_policy_agents.agents.orchestrator import build_brief, build_plan
from housing_policy_agents.models import ResearchProviderName, RunMode, UserResearchRequest


def test_live_assignments_include_manager_context_and_boundaries() -> None:
    request = UserResearchRequest(
        question=(
            "What would be the possible consequences if Fannie Mae and Freddie Mac began "
            "to purchase and guarantee manufactured-home chattel loans in the United States?"
        ),
        mode=RunMode.FAST,
        provider=ResearchProviderName.WEB,
        accept_defaults=True,
    )
    plan = build_plan(build_brief(request, clarification_enabled=False))
    government = next(item for item in plan.assignments if item.branch.value == "government_sources")

    assert "multi-agent" in government.research_context
    assert "Policy Research Manager" in government.research_context
    assert government.in_scope
    assert government.out_of_scope
    assert government.preferred_sources
    assert government.policy_decisions_supported
    assert any("short stable source IDs" in item for item in government.handoff_instructions)
    assert any("sibling" in item.lower() for item in government.required_questions)
