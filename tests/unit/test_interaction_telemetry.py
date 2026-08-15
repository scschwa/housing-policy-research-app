import json
from pathlib import Path
from shutil import rmtree
from types import SimpleNamespace
from uuid import uuid4

from housing_policy_agents.telemetry.interactions import InteractionTelemetry


def test_interaction_telemetry_persists_redacted_exchange() -> None:
    artifact_root = Path("work") / f"telemetry-test-{uuid4().hex}"
    artifact_root.mkdir(parents=True)
    telemetry = InteractionTelemetry(run_id="run-test", max_chars=200)
    interaction_id = telemetry.begin(
        agent="government_sources_researcher",
        stage="research",
        input_payload={"question": "housing", "api_key": "sk-12345678901234567890"},
    )
    assert interaction_id is not None
    telemetry.complete(
        interaction_id,
        SimpleNamespace(final_output={"status": "ok"}, new_items=[], raw_responses=[]),
    )
    telemetry.handoff(
        source="specialist_network",
        target="policy_research_manager",
        stage="manager_reconciliation",
        payload={"finding_count": 1},
    )

    try:
        telemetry.persist(artifact_root)

        summary = json.loads((artifact_root / "interaction_summary.json").read_text())
        request = json.loads(
            (
                artifact_root
                / "sub-agent-telemetry"
                / "001-government-sources-researcher"
                / "request.json"
            ).read_text()
        )
        assert summary["completed_count"] == 1
        assert summary["handoff_count"] == 1
        assert request["input"]["api_key"] == "[REDACTED]"
    finally:
        rmtree(artifact_root)


def test_interaction_telemetry_persists_runner_failure() -> None:
    artifact_root = Path("work") / f"telemetry-test-{uuid4().hex}"
    artifact_root.mkdir(parents=True)
    telemetry = InteractionTelemetry(run_id="run-test")
    interaction_id = telemetry.begin(
        agent="think_tank_academic_researcher",
        stage="research",
        input_payload={"assignment": "academic"},
    )
    assert interaction_id is not None
    telemetry.fail(interaction_id, ValueError("invalid structured output"))

    try:
        telemetry.persist(artifact_root)

        summary = json.loads((artifact_root / "interaction_summary.json").read_text())
        result = json.loads(
            (
                artifact_root
                / "sub-agent-telemetry"
                / "001-think-tank-academic-researcher"
                / "result.json"
            ).read_text()
        )
        assert summary["failed_count"] == 1
        assert result["error"]["type"] == "ValueError"
    finally:
        rmtree(artifact_root)
