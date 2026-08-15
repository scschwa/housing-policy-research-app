"""Bounded repair of report units that fail deterministic validation."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from ..context import RunContext
from ..models import (
    DraftReport,
    RepairStatus,
    ReportAuditEntry,
    ReportParagraph,
    ReportSection,
)
from ..telemetry.interactions import run_agent_with_telemetry
from ..tools.source_store import SourceLedger, ValidationIssue, ValidationReport, validate_report
from .factory import build_rework_agent


@dataclass
class ReworkOutcome:
    report: DraftReport
    entries: list[ReportAuditEntry]
    passes: int
    validation: ValidationReport


def _paragraph(report: DraftReport, paragraph_id: str) -> ReportParagraph | None:
    return next(
        (
            paragraph
            for section in report.sections
            for paragraph in section.paragraphs
            if paragraph.paragraph_id == paragraph_id
        ),
        None,
    )


def _content(report: DraftReport, issue: ValidationIssue) -> str:
    if issue.target_type == "paragraph":
        paragraph = _paragraph(report, issue.target_id)
        return paragraph.text if paragraph else "[paragraph unavailable]"
    if issue.target_type == "executive_summary":
        return report.executive_summary
    if issue.target_type == "decision_matrix":
        return json.dumps(report.decision_matrix.model_dump(mode="json"), indent=2)
    if issue.target_type == "source_ledger":
        return "Source-ledger validation affects the report's source appendix."
    return json.dumps(
        {
            "title": report.title,
            "section_ids": [section.section_id for section in report.sections],
        },
        indent=2,
    )


def _citations(report: DraftReport, issue: ValidationIssue) -> list[str]:
    if issue.target_type != "paragraph":
        return []
    paragraph = _paragraph(report, issue.target_id)
    return list(paragraph.citation_ids) if paragraph else []


def withhold_invalid_units(
    report: DraftReport, issues: list[ValidationIssue]
) -> DraftReport:
    withheld = report.model_copy(deep=True)
    components = set(withheld.withheld_components)
    for issue in issues:
        marker = f"[WITHHELD: {issue.message}]"
        if issue.target_type == "paragraph":
            paragraph = _paragraph(withheld, issue.target_id)
            if paragraph is not None:
                paragraph.text = marker
                paragraph.citation_ids = []
                paragraph.claim_ids = []
                paragraph.substantive = False
                paragraph.withheld = True
                paragraph.withheld_reason = issue.message
                components.add(issue.target_id)
        elif issue.target_type == "executive_summary":
            withheld.executive_summary = marker
            withheld.executive_summary_withheld = True
            components.add("executive_summary")
        elif issue.target_type == "decision_matrix":
            withheld.decision_matrix_withheld = True
            components.add("decision_matrix")
        elif issue.target_type == "source_ledger":
            components.add("sources")
            withheld.limitations.append(
                f"The source appendix is withheld pending correction: {issue.message}"
            )
        else:
            components.add(issue.target_id)
            withheld.limitations.append(f"A report-level validation issue remains: {issue.message}")
    withheld.withheld_components = sorted(components)
    return withheld


def _merge_authorized_changes(
    original: DraftReport,
    candidate: DraftReport,
    issues: list[ValidationIssue],
) -> DraftReport:
    merged = original.model_copy(deep=True)
    for issue in issues:
        if issue.target_type == "paragraph":
            source = _paragraph(candidate, issue.target_id)
            target = _paragraph(merged, issue.target_id)
            if source is not None and target is not None:
                replacement = source.model_copy(deep=True)
                target.text = replacement.text
                target.citation_ids = replacement.citation_ids
                target.claim_ids = replacement.claim_ids
                target.substantive = replacement.substantive
                target.revision_note = replacement.revision_note
                target.withheld = replacement.withheld
                target.withheld_reason = replacement.withheld_reason
        elif issue.target_type == "executive_summary":
            merged.executive_summary = candidate.executive_summary
            merged.executive_summary_withheld = candidate.executive_summary_withheld
        elif issue.target_type == "decision_matrix":
            merged.decision_matrix = candidate.decision_matrix.model_copy(deep=True)
            merged.decision_matrix_withheld = candidate.decision_matrix_withheld
        elif issue.target_type == "report":
            merged.sections = [section.model_copy(deep=True) for section in candidate.sections]
    components = set(candidate.withheld_components)
    components.update(
        paragraph.paragraph_id
        for section in merged.sections
        for paragraph in section.paragraphs
        if paragraph.withheld
    )
    if merged.executive_summary_withheld:
        components.add("executive_summary")
    if merged.decision_matrix_withheld:
        components.add("decision_matrix")
    merged.withheld_components = sorted(components)
    return merged


def _offline_candidate(
    report: DraftReport,
    issues: list[ValidationIssue],
    ledger: SourceLedger,
) -> DraftReport:
    candidate = report.model_copy(deep=True)
    for issue in issues:
        if issue.target_type == "paragraph":
            paragraph = _paragraph(candidate, issue.target_id)
            if paragraph is None:
                continue
            paragraph.citation_ids = [
                source_id for source_id in paragraph.citation_ids if source_id in ledger.ids()
            ]
            if paragraph.substantive and not paragraph.citation_ids:
                paragraph.text = f"[WITHHELD: {issue.message}]"
                paragraph.claim_ids = []
                paragraph.substantive = False
                paragraph.withheld = True
                paragraph.withheld_reason = issue.message
        elif issue.target_type == "executive_summary":
            candidate.executive_summary = f"[WITHHELD: {issue.message}]"
            candidate.executive_summary_withheld = True
        elif issue.target_type == "decision_matrix":
            if issue.code == "report.decision_matrix.invalid_citation":
                for option in candidate.decision_matrix.options:
                    option.source_ids = [
                        source_id for source_id in option.source_ids if source_id in ledger.ids()
                    ]
            else:
                candidate.decision_matrix_withheld = True
        elif issue.code == "report.sections.duplicate_ids":
            seen: dict[str, int] = {}
            for section in candidate.sections:
                seen[section.section_id] = seen.get(section.section_id, 0) + 1
                if seen[section.section_id] > 1:
                    section.section_id = f"{section.section_id}-{seen[section.section_id]}"
        elif issue.code == "report.sections.empty":
            candidate.sections = [
                ReportSection(
                    section_id="withheld",
                    title="Withheld",
                    paragraphs=[
                        ReportParagraph(
                            text=f"[WITHHELD: {issue.message}]",
                            substantive=False,
                            withheld=True,
                            withheld_reason=issue.message,
                        )
                    ],
                )
            ]
    return candidate


async def _live_candidate(
    report: DraftReport,
    withheld: DraftReport,
    validation: ValidationReport,
    ledger: SourceLedger,
    evidence: Any,
    context: RunContext,
    stage: str,
    pass_number: int,
) -> DraftReport:
    from agents import RunConfig

    agent = build_rework_agent(context.config)
    input_payload = {
        "original_report": report.model_dump(mode="json"),
        "withheld_report": withheld.model_dump(mode="json"),
        "validation_issues": [issue.__dict__ for issue in validation.issues],
        "source_ledger": [source.model_dump(mode="json") for source in ledger.values()],
        "evidence_package": evidence,
        "repair_contract": {
            "stage": stage,
            "pass": pass_number,
            "authorized_targets": [issue.target_id for issue in validation.issues],
            "max_passes": context.config.max_rework_passes,
        },
    }
    result = await run_agent_with_telemetry(
        context=context,
        agent=agent,
        runner_input=json.dumps(input_payload, indent=2),
        input_payload=input_payload,
        agent_name="validation_rework_specialist",
        stage=f"{stage}_rework_pass_{pass_number}",
        max_turns=max(1, min(context.config.max_turns_per_agent, 3)),
        run_config=RunConfig(
            model=context.config.openai_model,
            workflow_name="Housing Policy Research Network",
            trace_id=context.trace_id,
            trace_include_sensitive_data=context.config.trace_include_sensitive_data,
            trace_metadata={
                "run_id": context.run_id,
                "stage": stage,
                "rework_pass": str(pass_number),
            },
        ),
    )
    if not isinstance(result.final_output, DraftReport):
        raise TypeError("re-work specialist did not return DraftReport")
    return result.final_output


def _audit_entries(
    *,
    original: DraftReport,
    final: DraftReport,
    issues: list[ValidationIssue],
    stage: str,
    passes: int,
    final_validation: ValidationReport,
) -> list[ReportAuditEntry]:
    unresolved = {
        (issue.code, issue.target_type, issue.target_id) for issue in final_validation.issues
    }
    withheld = withhold_invalid_units(original, issues)
    entries: list[ReportAuditEntry] = []
    for issue in issues:
        final_paragraph = (
            _paragraph(final, issue.target_id) if issue.target_type == "paragraph" else None
        )
        remains_withheld = bool(final_paragraph and final_paragraph.withheld)
        if issue.target_type == "executive_summary":
            remains_withheld = final.executive_summary_withheld
        elif issue.target_type == "decision_matrix":
            remains_withheld = final.decision_matrix_withheld
        unresolved_key = (issue.code, issue.target_type, issue.target_id) in unresolved
        revised_content = _content(final, issue)
        original_content = _content(original, issue)
        citations_before = _citations(original, issue)
        citations_after = _citations(final, issue)
        if remains_withheld or unresolved_key:
            status = RepairStatus.WITHHELD
        elif revised_content != original_content or citations_after != citations_before:
            status = RepairStatus.REPAIRED
        else:
            status = RepairStatus.UNCHANGED
        entries.append(
            ReportAuditEntry(
                stage=stage,
                issue_code=issue.code,
                issue=issue.message,
                target_type=issue.target_type,
                target_id=issue.target_id,
                section_id=issue.section_id,
                original_content=original_content,
                withheld_content=_content(withheld, issue),
                revised_content=revised_content,
                status=status,
                attempts=passes,
                citation_ids_before=citations_before,
                citation_ids_after=citations_after,
                notes=(
                    ["The issue remained unresolved after bounded re-work."]
                    if unresolved_key
                    else []
                ),
            )
        )
    return entries


async def rework_validation_failures(
    *,
    report: DraftReport,
    validation: ValidationReport,
    ledger: SourceLedger,
    evidence: Any,
    context: RunContext,
    stage: str,
) -> ReworkOutcome:
    if not validation.errors:
        return ReworkOutcome(report=report, entries=[], passes=0, validation=validation)

    original = report.model_copy(deep=True)
    working = report.model_copy(deep=True)
    current = validation
    all_issues: dict[tuple[str, str, str], ValidationIssue] = {
        (issue.code, issue.target_type, issue.target_id): issue for issue in current.issues
    }
    passes = 0
    for pass_number in range(1, context.config.max_rework_passes + 1):
        passes = pass_number
        withheld = withhold_invalid_units(working, current.issues)
        try:
            if context.config.research_provider == "offline":
                candidate = _offline_candidate(working, current.issues, ledger)
                telemetry = context.interaction_telemetry
                if telemetry is not None:
                    telemetry.record_local(
                        agent="validation_rework_specialist",
                        stage=f"{stage}_rework_pass_{pass_number}",
                        duration_ms=0,
                    )
            else:
                candidate = await asyncio.wait_for(
                    _live_candidate(
                        working,
                        withheld,
                        current,
                        ledger,
                        evidence,
                        context,
                        stage,
                        pass_number,
                    ),
                    timeout=context.config.rework_timeout_seconds,
                )
            working = _merge_authorized_changes(working, candidate, current.issues)
        except Exception as exc:
            context.metadata.setdefault("rework_failures", []).append(
                f"{stage} pass {pass_number}: {type(exc).__name__}: {exc}"
            )
            working = withheld
            break
        current = validate_report(working, ledger)
        for issue in current.issues:
            all_issues[(issue.code, issue.target_type, issue.target_id)] = issue
        if not current.errors:
            break

    if current.errors:
        working = withhold_invalid_units(working, current.issues)
        current = validate_report(working, ledger)

    entries = _audit_entries(
        original=original,
        final=working,
        issues=list(all_issues.values()),
        stage=stage,
        passes=passes,
        final_validation=current,
    )
    working.revised = True
    working.revision_count = max(working.revision_count, original.revision_count + 1)
    return ReworkOutcome(
        report=working,
        entries=entries,
        passes=passes,
        validation=current,
    )
