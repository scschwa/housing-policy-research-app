"""Readable Markdown rendering with source-ledger hyperlinks."""

from __future__ import annotations

import json
from pathlib import Path

from ..models import DraftReport, FinalResearchPackage
from ..tools.source_store import SourceLedger, citation_link


def render_markdown(report: DraftReport, ledger: SourceLedger) -> str:
    lines = [f"# {report.title}", "", "## Executive summary", "", report.executive_summary, ""]
    for section in report.sections:
        lines.extend([f"## {section.title}", ""])
        for paragraph in section.paragraphs:
            citations = " ".join(citation_link(source_id) for source_id in paragraph.citation_ids)
            lines.append(paragraph.text + (f" {citations}" if citations else ""))
            if paragraph.revision_note:
                lines.append(f"\n> Revision note: {paragraph.revision_note}")
            lines.append("")
        if section.section_id == "decision_matrix":
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
            matrix.scores[option.option_id][criterion.criterion_id] for criterion in matrix.criteria
        ]
        lines.append("| " + " | ".join(row) + " |")
    lines.extend(["", "**Matrix caveats:**", ""])
    lines.extend(f"- {caveat}" for caveat in matrix.caveats)
    return lines + [""]


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
    return artifact_dir
