"""Primary command-line interface."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

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
from .telemetry.metrics import ProgressCallback
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


def _display_progress(event: str, metadata: dict[str, object]) -> None:
    """Print bounded, non-sensitive workflow progress for CLI users."""

    def label(value: object) -> str:
        return str(value).replace("_", " ").title()

    if event == "run_started":
        console.print(f"[bold cyan]Starting {label(metadata.get('provider', 'research'))} research[/bold cyan]")
    elif event == "intake_validated":
        console.print("[cyan]OK - Intake accepted; applying research defaults[/cyan]")
    elif event == "plan_created":
        branches = metadata.get("branches", [])
        branch_count = len(branches) if isinstance(branches, list) else 0
        console.print(f"[cyan]OK - Research plan created ({branch_count} branches)[/cyan]")
    elif event == "research_started":
        console.print(f"[cyan]Researching {metadata.get('assignments', 0)} assignments...[/cyan]")
    elif event == "branch_started":
        console.print(f"  [dim]-> Branch started: {label(metadata.get('branch', 'unknown'))}[/dim]")
    elif event == "branch_finished":
        console.print(
            f"  [green]OK - Branch finished: {label(metadata.get('branch', 'unknown'))} "
            f"({label(metadata.get('status', 'unknown'))}; attempts={metadata.get('attempts', 1)})[/green]"
        )
    elif event == "branches_validated":
        console.print(
            f"[cyan]OK - Evidence checked (errors={metadata.get('errors', 0)}, "
            f"warnings={metadata.get('warnings', 0)})[/cyan]"
        )
    elif event == "manager_started":
        console.print(f"[cyan]Reconciling {label(metadata.get('manager', 'manager'))}...[/cyan]")
    elif event == "manager_finished":
        console.print(f"[green]OK - Manager synthesis complete: {label(metadata.get('manager', 'manager'))}[/green]")
    elif event == "managers_reconciled":
        console.print(f"[cyan]OK - Manager layer complete ({metadata.get('count', 0)} managers)[/cyan]")
    elif event == "draft_started":
        console.print("[cyan]Writing evidence-grounded draft report...[/cyan]")
    elif event == "draft_completed":
        console.print(f"[green]OK - Draft report complete ({metadata.get('sections', 0)} sections)[/green]")
    elif event == "draft_retry_used":
        console.print(
            "[yellow]Draft completed through the bounded compact retry after the initial "
            "structured output failed.[/yellow]"
        )
    elif event == "draft_fallback":
        console.print(
            f"[yellow]OK - Draft fallback used; synthesis withheld ({metadata.get('reason', 'typed output failure')})[/yellow]"
        )
    elif event == "pre_review_validation":
        console.print(
            f"[cyan]OK - Pre-review validation complete (errors={metadata.get('errors', 0)}, "
            f"warnings={metadata.get('warnings', 0)})[/cyan]"
        )
    elif event == "review_started":
        console.print("[cyan]Running adversarial review...[/cyan]")
    elif event == "review_completed":
        console.print(
            f"[green]OK - Review complete: {label(metadata.get('recommendation', 'unknown'))} "
            f"({metadata.get('findings', 0)} findings)[/green]"
        )
    elif event == "review_skipped":
        console.print("[yellow]Adversarial review skipped by configuration[/yellow]")
    elif event == "revision_started":
        console.print("[cyan]Applying bounded report revision...[/cyan]")
    elif event == "bounded_revision":
        if metadata.get("fallback"):
            console.print("[yellow]OK - Revision fallback used; retaining validated draft[/yellow]")
        else:
            console.print(f"[green]OK - Revision complete (revision={metadata.get('revision_count', 0)})[/green]")
    elif event == "revision_fallback":
        console.print(
            f"[yellow]Revision fallback: {metadata.get('reason', 'revision unavailable')}; "
            "retaining validated draft[/yellow]"
        )
    elif event == "final_validation":
        console.print(
            f"[cyan]OK - Final validation complete (errors={metadata.get('errors', 0)}, "
            f"warnings={metadata.get('warnings', 0)})[/cyan]"
        )
    elif event == "validation_rework_started":
        console.print(
            f"[yellow]Validation re-work started ({label(metadata.get('stage', 'report'))}; "
            f"issues={metadata.get('errors', 0)})[/yellow]"
        )
    elif event == "validation_rework_completed":
        console.print(
            f"[green]OK - Validation re-work complete "
            f"({label(metadata.get('stage', 'report'))}; passes={metadata.get('passes', 0)}; "
            f"withheld={metadata.get('withheld', 0)}; "
            f"remaining={metadata.get('remaining_errors', 0)})[/green]"
        )
    elif event == "artifacts_persisted":
        console.print(f"[green]OK - Artifacts written to {metadata.get('path', 'artifacts')}[/green]")


def _display_usage_summary(package: FinalResearchPackage) -> None:
    usage = package.usage_report
    if usage is None:
        return
    cost = (
        f"${usage.approximate_cost_usd:.8f}"
        if usage.approximate_cost_usd is not None
        else "unavailable"
    )
    console.print(
        "\n[bold]Usage summary[/bold]: "
        f"requests={usage.requests}; input={usage.input_tokens:,}; "
        f"output={usage.output_tokens:,}; total={usage.total_tokens:,}; "
        f"wall={usage.wall_clock_ms / 1000:.2f}s; estimated token cost={cost}"
    )
    if not usage.records:
        return
    table = Table(title="Agent and sub-agent usage", show_lines=False)
    table.add_column("Agent")
    table.add_column("Stage")
    table.add_column("Tokens", justify="right")
    table.add_column("Time", justify="right")
    table.add_column("Est. token cost", justify="right")
    for record in sorted(
        usage.records,
        key=lambda item: (item.total_tokens, item.duration_ms),
        reverse=True,
    ):
        record_cost = (
            f"${record.approximate_cost_usd:.8f}"
            if record.approximate_cost_usd is not None
            else "n/a"
        )
        table.add_row(
            record.agent,
            record.stage,
            f"{record.total_tokens:,}",
            f"{record.duration_ms / 1000:.2f}s",
            record_cost,
        )
    console.print(table)


async def _run_request(
    request: UserResearchRequest,
    provider: ResearchProviderName,
    answers: dict[str, str],
    progress_callback: ProgressCallback | None = None,
) -> FinalResearchPackage:
    workflow = ResearchWorkflow(_config(provider))
    return await workflow.run(request, answers, progress_callback=progress_callback)


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
        str,
        typer.Option(
            "--format",
            help="Compatibility option; Markdown and JSON are written to artifacts, not stdout.",
        ),
    ] = "both",
) -> None:
    """Run an interactive or fast research request."""
    del output_format
    mode = RunMode.FAST if fast else RunMode.INTERACTIVE
    request = UserResearchRequest(
        question=question, mode=mode, provider=provider, accept_defaults=fast
    )
    questions = decide_clarifications(request).questions
    answers = _answers(questions, fast)
    try:
        package = asyncio.run(_run_request(request, provider, answers, _display_progress))
    except WorkflowError as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print(f"\n[green]Run complete:[/green] {package.run_id}")
    console.print(f"Artifacts: {(Path('artifacts') / package.metrics.run_id).as_posix()}")
    _display_usage_summary(package)


@app.command()
def demo(
    offline: bool = typer.Option(
        True, "--offline/--live", help="Run the deterministic fixture demo."
    ),
    output_format: str = typer.Option(
        "both",
        "--format",
        help="Compatibility option; Markdown and JSON are written to artifacts, not stdout.",
    ),
) -> None:
    """Run the required mortgage-portability demonstration."""
    del output_format
    provider = ResearchProviderName.OFFLINE if offline else ResearchProviderName.WEB
    request = UserResearchRequest(
        question=DEMO_QUESTION, mode=RunMode.FAST, provider=provider, accept_defaults=True
    )
    try:
        package = asyncio.run(_run_request(request, provider, {}, _display_progress))
    except WorkflowError as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print(f"[green]Demo complete:[/green] {package.run_id}")
    artifact_dir = Path("artifacts") / package.run_id
    console.print(f"Artifacts: {artifact_dir}")
    _display_usage_summary(package)


@app.command()
def graph(format: str = typer.Option("mermaid", "--format", help="mermaid or ascii")) -> None:
    """Print the configured agent graph."""
    if format == "mermaid":
        typer.echo(mermaid_graph())
        return
    typer.echo(
        "Orchestrator -> Policy | Industry | Advocacy | Global -> Specialists -> Writer -> Validator -> Re-work -> Reviewer -> Revision -> Final validation/Re-work -> Artifacts"
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
