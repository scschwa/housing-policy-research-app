"""Readable Markdown rendering with source-ledger hyperlinks."""

from __future__ import annotations

import json
from pathlib import Path

from ..models import (
    DecisionScoreDetail,
    DraftReport,
    FinalResearchPackage,
    ReportAudit,
    UsageReport,
)
from ..tools.source_store import SourceLedger, citation_link


def render_markdown(report: DraftReport, ledger: SourceLedger) -> str:
    lines = [f"# {report.title}", "", "## Executive summary", "", report.executive_summary, ""]
    if report.executive_summary_withheld:
        lines.extend([
            "> This executive summary remains withheld because it did not pass bounded validation re-work.",
            "",
        ])
    for section in report.sections:
        lines.extend([f"## {section.title}", ""])
        for paragraph in section.paragraphs:
            if paragraph.withheld:
                lines.append(
                    f"> {paragraph.text}"
                    + (f" Reason: {paragraph.withheld_reason}" if paragraph.withheld_reason else "")
                )
                lines.append("")
                continue
            citations = " ".join(citation_link(source_id) for source_id in paragraph.citation_ids)
            lines.append(paragraph.text + (f" {citations}" if citations else ""))
            if paragraph.revision_note:
                lines.append(f"\n> Revision note: {paragraph.revision_note}")
            lines.append("")
        if section.section_id == "decision_matrix":
            if report.decision_matrix_withheld:
                lines.extend([
                    "> Decision matrix withheld because it did not pass bounded validation re-work.",
                    "",
                ])
            else:
                lines.extend(render_decision_matrix(report))
    lines.extend(["## Disclosures", ""])
    lines.extend(f"- {disclosure}" for disclosure in report.disclosures)
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report.limitations)
    return "\n".join(lines).rstrip() + "\n"


def render_decision_matrix(report: DraftReport) -> list[str]:
    matrix = report.decision_matrix
    header = ["Option"] + [criterion.name for criterion in matrix.criteria]
    lines = ["", "| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
    for option in matrix.options:
        row = [option.name] + [
            _format_score(matrix.scores[option.option_id][criterion.criterion_id])
            for criterion in matrix.criteria
        ]
        lines.append("| " + " | ".join(row) + " |")
    lines.extend(["", "**Matrix caveats:**", ""])
    lines.extend(f"- {caveat}" for caveat in matrix.caveats)
    return lines + [""]


def _format_score(score: object) -> str:
    if isinstance(score, DecisionScoreDetail):
        text = score.range if not score.note else f"{score.range}: {score.note}"
    else:
        text = str(score)
    return text.replace("|", "\\|").replace("\n", " ")


def _quote_block(value: str) -> list[str]:
    return [f"> {line}" if line else ">" for line in value.splitlines()]


def render_audit_report(audit: ReportAudit) -> str:
    lines = [
        "# Validation and re-work audit report",
        "",
        f"- **Run:** `{audit.run_id}`",
        f"- **Initial validation errors:** {audit.initial_error_count}",
        f"- **Re-work passes:** {audit.repair_passes}",
        f"- **Final validation errors:** {audit.final_error_count}",
        "",
    ]
    if not audit.entries:
        lines.extend(["No report component failed deterministic validation.", ""])
        return "\n".join(lines)

    for index, entry in enumerate(audit.entries, start=1):
        lines.extend(
            [
                f"## {index}. {entry.issue_code}",
                "",
                f"- **Stage:** {entry.stage}",
                f"- **Target:** `{entry.target_type}:{entry.target_id}`",
                f"- **Section:** `{entry.section_id or 'not specified'}`",
                f"- **Disposition:** **{entry.status.value}**",
                f"- **Repair attempts:** {entry.attempts}",
                f"- **Flag:** {entry.issue}",
                f"- **Citations before:** {', '.join(entry.citation_ids_before) or 'none'}",
                f"- **Citations after:** {', '.join(entry.citation_ids_after) or 'none'}",
                "",
                "### Original",
                "",
                *_quote_block(entry.original_content),
                "",
                "### Withheld representation",
                "",
                *_quote_block(entry.withheld_content),
                "",
                "### Final report representation",
                "",
                *_quote_block(entry.revised_content or "[no replacement produced]"),
                "",
            ]
        )
        if entry.notes:
            lines.extend(["### Notes", "", *[f"- {note}" for note in entry.notes], ""])
    return "\n".join(lines).rstrip() + "\n"


def render_usage_report(usage: UsageReport) -> str:
    cost = (
        f"${usage.approximate_cost_usd:.8f}"
        if usage.approximate_cost_usd is not None
        else "not available"
    )
    lines = [
        "# Usage report",
        "",
        f"- **Run:** `{usage.run_id}`",
        f"- **Model:** `{usage.model or 'not recorded'}`",
        f"- **Requests:** {usage.requests:,}",
        f"- **Input tokens:** {usage.input_tokens:,}",
        f"- **Cached input tokens:** {usage.cached_input_tokens:,}",
        f"- **Cache-write tokens:** {usage.cache_write_tokens:,}",
        f"- **Output tokens:** {usage.output_tokens:,}",
        f"- **Reasoning tokens:** {usage.reasoning_tokens:,}",
        f"- **Total tokens:** {usage.total_tokens:,}",
        f"- **Wall-clock time:** {usage.wall_clock_ms / 1000:.2f} seconds",
        f"- **Cumulative agent time:** {usage.cumulative_agent_ms / 1000:.2f} seconds",
        f"- **Estimated token cost:** {cost}",
        "",
        usage.pricing_note,
        "",
        usage.concurrency_note,
        "",
        "## Agent and sub-agent breakdown",
        "",
        "| Agent | Stage | Model | Status | Requests | Input | Cached | Cache write | Output | Reasoning | Total | Time (s) | Est. token cost |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for record in usage.records:
        record_cost = (
            f"${record.approximate_cost_usd:.8f}"
            if record.approximate_cost_usd is not None
            else "n/a"
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    record.agent.replace("|", "\\|"),
                    record.stage.replace("|", "\\|"),
                    (record.model or "n/a").replace("|", "\\|"),
                    record.status,
                    str(record.requests),
                    f"{record.input_tokens:,}",
                    f"{record.cached_input_tokens:,}",
                    f"{record.cache_write_tokens:,}",
                    f"{record.output_tokens:,}",
                    f"{record.reasoning_tokens:,}",
                    f"{record.total_tokens:,}",
                    f"{record.duration_ms / 1000:.2f}",
                    record_cost,
                ]
            )
            + " |"
        )
    priced_records = {
        (
            record.model or "n/a",
            record.pricing_model or "n/a",
            record.input_rate_per_million_usd,
            record.cached_input_rate_per_million_usd,
            record.cache_write_rate_per_million_usd,
            record.output_rate_per_million_usd,
            record.pricing_source_url,
        )
        for record in usage.records
        if record.pricing_model is not None
    }
    if priced_records:
        lines.extend(
            [
                "",
                "## Pricing basis",
                "",
                "Rates are USD per one million tokens. Cache-write rates equal regular input rates where OpenAI does not publish a distinct write rate.",
                "",
                "| Requested model | Pricing model | Input | Cached input | Cache write | Output | Source |",
                "| --- | --- | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for requested, pricing_model, input_rate, cached_rate, write_rate, output_rate, source in sorted(
            priced_records
        ):
            source_label = (
                f"[official model page]({source})"
                if source and source.startswith("https://")
                else str(source or "configuration")
            )
            lines.append(
                f"| {requested} | {pricing_model} | {input_rate:.3f} | "
                f"{cached_rate:.3f} | {write_rate:.3f} | {output_rate:.3f} | "
                f"{source_label} |"
            )
    return "\n".join(lines).rstrip() + "\n"


def persist_package(package: FinalResearchPackage, root: Path) -> Path:
    artifact_dir = root / package.run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    payload = package.model_dump(mode="json")
    (artifact_dir / "package.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (artifact_dir / "brief.json").write_text(
        json.dumps(package.brief.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    (artifact_dir / "plan.json").write_text(
        json.dumps(package.plan.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    (artifact_dir / "sources.json").write_text(
        json.dumps([item.model_dump(mode="json") for item in package.source_ledger], indent=2),
        encoding="utf-8",
    )
    (artifact_dir / "sources.md").write_text(
        SourceLedger(package.source_ledger).markdown(), encoding="utf-8"
    )
    (artifact_dir / "draft_report.json").write_text(
        json.dumps(package.draft_report.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    (artifact_dir / "review.json").write_text(
        json.dumps(package.adversarial_review.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    (artifact_dir / "final_report.json").write_text(
        json.dumps(package.final_report.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    (artifact_dir / "report.md").write_text(
        render_markdown(package.final_report, SourceLedger(package.source_ledger)), encoding="utf-8"
    )
    (artifact_dir / "metrics.json").write_text(
        json.dumps(package.metrics.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    if package.audit_report is not None:
        (artifact_dir / "audit_report.json").write_text(
            json.dumps(package.audit_report.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        (artifact_dir / "audit_report.md").write_text(
            render_audit_report(package.audit_report), encoding="utf-8"
        )
    if package.usage_report is not None:
        (artifact_dir / "usage_report.json").write_text(
            json.dumps(package.usage_report.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        (artifact_dir / "usage_report.md").write_text(
            render_usage_report(package.usage_report), encoding="utf-8"
        )
    return artifact_dir
