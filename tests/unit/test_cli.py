from types import SimpleNamespace

from typer.testing import CliRunner

from housing_policy_agents import cli


class _FileOnlyPackage:
    run_id = "run-cli-test"
    metrics = SimpleNamespace(run_id=run_id)
    usage_report = SimpleNamespace(
        approximate_cost_usd=0.01234567,
        requests=2,
        input_tokens=1000,
        output_tokens=500,
        total_tokens=1500,
        wall_clock_ms=2000,
        records=[],
    )

    def model_dump(self, *args: object, **kwargs: object) -> dict[str, object]:
        del args, kwargs
        raise AssertionError("The CLI must not serialize the package to stdout")

    @property
    def final_report(self) -> object:
        raise AssertionError("The CLI must not render the report to stdout")


def test_ask_prints_status_and_usage_without_raw_report(monkeypatch: object) -> None:
    async def fake_run_request(*args: object, **kwargs: object) -> _FileOnlyPackage:
        del args, kwargs
        return _FileOnlyPackage()

    monkeypatch.setattr(  # type: ignore[attr-defined]
        cli,
        "decide_clarifications",
        lambda request: SimpleNamespace(questions=[]),
    )
    monkeypatch.setattr(cli, "_run_request", fake_run_request)  # type: ignore[attr-defined]

    result = CliRunner().invoke(
        cli.app,
        ["ask", "How should housing supply be expanded?", "--fast", "--format", "both"],
    )

    assert result.exit_code == 0
    assert "Run complete: run-cli-test" in result.stdout
    assert "Artifacts: artifacts/run-cli-test" in result.stdout
    assert "Usage summary" in result.stdout
    assert "estimated token cost=$0.01234567" in result.stdout
