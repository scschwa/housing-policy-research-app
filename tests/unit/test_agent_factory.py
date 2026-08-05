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
