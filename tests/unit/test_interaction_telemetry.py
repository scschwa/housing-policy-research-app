import json
from pathlib import Path
from shutil import rmtree
from types import SimpleNamespace
from uuid import uuid4

from housing_policy_agents.config import AppConfig
from housing_policy_agents.telemetry.interactions import InteractionTelemetry
from housing_policy_agents.telemetry.usage import build_usage_report


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
    usage = SimpleNamespace(
        requests=1,
        input_tokens=400,
        output_tokens=200,
        total_tokens=600,
        input_tokens_details=SimpleNamespace(cached_tokens=100, cache_write_tokens=0),
        output_tokens_details=SimpleNamespace(reasoning_tokens=50),
    )
    telemetry.fail(
        interaction_id,
        ValueError("invalid structured output"),
        raw_responses=[SimpleNamespace(usage=usage, response_id="resp-failed")],
    )

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
        assert result["usage"]["total_tokens"] == 600
        assert result["response_ids"] == ["resp-failed"]
    finally:
        rmtree(artifact_root)


def test_usage_report_aggregates_sdk_usage_and_configured_cost() -> None:
    telemetry = InteractionTelemetry(run_id="run-usage-test")
    interaction_id = telemetry.begin(
        agent="synthesis_writer",
        stage="draft",
        input_payload={},
        metadata={"model": "test-model"},
    )
    usage = SimpleNamespace(
        requests=1,
        input_tokens=1000,
        output_tokens=500,
        total_tokens=1500,
        input_tokens_details=SimpleNamespace(
            cached_tokens=200,
            cache_write_tokens=50,
        ),
        output_tokens_details=SimpleNamespace(reasoning_tokens=125),
    )
    telemetry.complete(
        interaction_id,
        SimpleNamespace(
            final_output={"status": "ok"},
            new_items=[],
            raw_responses=[SimpleNamespace(usage=usage, response_id="resp-test")],
        ),
    )
    report = build_usage_report(
        run_id="run-usage-test",
        telemetry=telemetry,
        config=AppConfig(
            openai_input_cost_per_million_usd=2.0,
            openai_cached_input_cost_per_million_usd=0.5,
            openai_output_cost_per_million_usd=8.0,
        ),
        wall_clock_ms=2000,
    )

    assert report.requests == 1
    assert report.input_tokens == 1000
    assert report.cached_input_tokens == 200
    assert report.output_tokens == 500
    assert report.reasoning_tokens == 125
    assert report.total_tokens == 1500
    assert report.approximate_cost_usd == 0.0057
    assert report.records[0].model == "test-model"
