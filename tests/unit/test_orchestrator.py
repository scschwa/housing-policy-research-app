from housing_policy_agents.agents.orchestrator import build_brief, build_plan
from housing_policy_agents.models import (
    MAX_SEARCH_QUERY_CHARS,
    ResearchProviderName,
    RunMode,
    UserResearchRequest,
)


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


def test_long_question_preserves_full_context_with_bounded_search_hints() -> None:
    question = (
        "FHFA is considering changing the Area Median Income Calculation for housing goal "
        "determination to be the maxium of a county, state, or the US, bifurcated by being "
        "in a metropolitan statistical area or not (proposal 1). They are also considering "
        "grouping micropolitan areas in with metropolitan areas so that it would be bifurcated "
        "by in CBSA or not (proposal 2). Separately from this, I am proposing that they might "
        "want to consider USDA-RUCA's instead and do a trifuraction where they take the max "
        "income across [tract, state, us], where this is determined by urban = USDA-RUCA=(1 or "
        "2), semi-urban = USDA-RUCA=(4,5) and then Rural/ex-urban = 3, 6, 7+. What are the pros, "
        "cons, and potential externalties of adopting one of these approaches?"
    )
    assert len(question) > MAX_SEARCH_QUERY_CHARS

    request = UserResearchRequest(
        question=question,
        mode=RunMode.FAST,
        provider=ResearchProviderName.WEB,
        accept_defaults=True,
    )
    plan = build_plan(build_brief(request, clarification_enabled=False))

    assert plan.brief.question == question
    assert plan.assignments
    for assignment in plan.assignments:
        assert question in assignment.required_questions[0]
        assert assignment.search_queries
        search_text = assignment.search_queries[0].text
        assert len(search_text) <= MAX_SEARCH_QUERY_CHARS
        assert search_text.startswith("FHFA is considering")
        assert "potential externalties" in search_text
