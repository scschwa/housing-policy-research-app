"""Primary command-line interface."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from .agents.factory import mermaid_graph
from .agents.orchestrator import decide_clarifications
from .config import AppConfig
from .models import (
    ClarificationQuestion,
    FinalResearchPackage,
    ResearchProviderName,
    RunMode,
    UserResearchRequest,
)
from .reporting.render import render_markdown
from .tools.source_store import SourceLedger, validate_report
from .workflows.research_workflow import ResearchWorkflow, WorkflowError

app = typer.Typer(help="Housing Policy Research Network CLI")
console = Console()

DEMO_QUESTION = (
    "The United States is considering a policy that would permit qualifying borrowers to transfer "
    "an existing low-rate mortgage to a newly purchased primary residence. Evaluate possible policy "
    "designs, consumer effects, legal and operational barriers, mortgage-market and taxpayer risks, "
    "distributional consequences, and relevant international precedents."
)


def _fixture_path() -> Path:
    candidate = Path.cwd() / "tests" / "fixtures" / "mortgage_portability.json"
    if candidate.exists():
        return candidate
    return Path(__file__).parents[3] / "tests" / "fixtures" / "mortgage_portability.json"


def _config(provider: ResearchProviderName) -> AppConfig:
    return AppConfig(
        research_provider=provider.value,
        allow_network=provider == ResearchProviderName.WEB,
        fixture_path=_fixture_path(),
    )


def _answers(questions: Sequence[ClarificationQuestion], fast: bool) -> dict[str, str]:
    if fast:
        return {}
    answers: dict[str, str] = {}
    for question in questions:
        console.print(f"\n[bold]{question.prompt}[/bold]")
        if question.options:
            console.print("Options: " + "; ".join(question.options))
        answer = typer.prompt("Answer (press Enter for default)", default=question.default or "")
        if answer:
            answers[question.question_id] = answer
    return answers


async def _run_request(
    request: UserResearchRequest, provider: ResearchProviderName, answers: dict[str, str]
) -> FinalResearchPackage:
    workflow = ResearchWorkflow(_config(provider))
    return await workflow.run(request, answers)


@app.command()
def ask(
    question: Annotated[str, typer.Argument(help="Housing-policy research question.")],
    fast: Annotated[
        bool, typer.Option("--fast", help="Use transparent defaults without clarification.")
    ] = False,
    provider: Annotated[
        ResearchProviderName, typer.Option("--provider")
    ] = ResearchProviderName.OFFLINE,
    output_format: Annotated[
        str, typer.Option("--format", help="markdown, json, or both")
    ] = "both",
) -> None:
    """Run an interactive or fast research request."""
    mode = RunMode.FAST if fast else RunMode.INTERACTIVE
    request = UserResearchRequest(
        question=question, mode=mode, provider=provider, accept_defaults=fast
    )
    questions = decide_clarifications(request).questions
    answers = _answers(questions, fast)
    try:
        package = asyncio.run(_run_request(request, provider, answers))
    except WorkflowError as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print(f"\n[green]Run complete:[/green] {package.run_id}")
    console.print(f"Artifacts: {(Path('artifacts') / package.metrics.run_id).as_posix()}")
    if output_format in {"json", "both"}:
        console.print(json.dumps(package.model_dump(mode="json"), indent=2))
    if output_format in {"markdown", "both"}:
        console.print(render_markdown(package.final_report, SourceLedger(package.source_ledger)))


@app.command()
def demo(
    offline: bool = typer.Option(
        True, "--offline/--live", help="Run the deterministic fixture demo."
    ),
    output_format: str = typer.Option("both", "--format"),
) -> None:
    """Run the required mortgage-portability demonstration."""
    provider = ResearchProviderName.OFFLINE if offline else ResearchProviderName.WEB
    request = UserResearchRequest(
        question=DEMO_QUESTION, mode=RunMode.FAST, provider=provider, accept_defaults=True
    )
    try:
        package = asyncio.run(_run_request(request, provider, {}))
    except WorkflowError as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print(f"[green]Demo complete:[/green] {package.run_id}")
    artifact_dir = Path("artifacts") / package.run_id
    console.print(f"Artifacts: {artifact_dir}")
    if output_format in {"json", "both"}:
        console.print(json.dumps(package.model_dump(mode="json"), indent=2))
    if output_format in {"markdown", "both"}:
        console.print(render_markdown(package.final_report, SourceLedger(package.source_ledger)))


@app.command()
def graph(format: str = typer.Option("mermaid", "--format", help="mermaid or ascii")) -> None:
    """Print the configured agent graph."""
    if format == "mermaid":
        typer.echo(mermaid_graph())
        return
    typer.echo(
        "Orchestrator -> Policy | Industry | Advocacy | Global -> Specialists -> Writer -> Validator -> Reviewer -> Revision -> Artifacts"
    )


@app.command()
def validate(package_path: Annotated[Path, typer.Argument(exists=True, readable=True)]) -> None:
    """Validate a saved FinalResearchPackage JSON artifact."""
    from .models import FinalResearchPackage

    package = FinalResearchPackage.model_validate_json(package_path.read_text(encoding="utf-8"))
    report = validate_report(package.final_report, SourceLedger(package.source_ledger))
    if report.errors:
        console.print_json(
            json.dumps({"ok": False, "errors": report.errors, "warnings": report.warnings})
        )
        raise typer.Exit(code=1)
    console.print_json(json.dumps({"ok": True, "errors": [], "warnings": report.warnings}))


if __name__ == "__main__":
    app()
