from agents import AgentOutputSchema

from housing_policy_agents.agents.factory import build_agent_graph
from housing_policy_agents.config import AppConfig


def test_agent_graph_relaxes_only_sdk_incompatible_mapping_schemas() -> None:
    graph = build_agent_graph(AppConfig())

    manager_output = graph["managers"]["policy_research_manager"].output_type
    writer_output = graph["writer"].output_type
    specialist_output = graph["specialists"]["government_sources"].output_type

    assert isinstance(manager_output, AgentOutputSchema)
    assert isinstance(writer_output, AgentOutputSchema)
    assert isinstance(specialist_output, AgentOutputSchema)
    assert not manager_output.is_strict_json_schema()
    assert not writer_output.is_strict_json_schema()
    assert specialist_output.is_strict_json_schema()


def test_agent_instructions_define_roles_and_source_id_contract() -> None:
    graph = build_agent_graph(AppConfig())

    specialist_instructions = graph["specialists"]["government_sources"].instructions
    manager_instructions = graph["managers"]["policy_research_manager"].instructions

    assert "Government Sources Researcher" in specialist_instructions
    assert "source_id" in specialist_instructions
    assert "complete web address only in the source record's `url` field" in specialist_instructions
    assert "evidence integrator" in manager_instructions
    assert "Return exactly one `ManagerSynthesis` object" in manager_instructions
