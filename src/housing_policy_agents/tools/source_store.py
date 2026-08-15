"""Normalized source ledger and citation reference checks."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from ..models import CountryComparison, DraftReport, EvidenceClaim, SourceRecord


def normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    return url.strip().rstrip("/").lower()


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class SourceLedger:
    """Deduplicates sources while preserving provenance and safety flags."""

    records: dict[str, SourceRecord]
    aliases: dict[str, str]

    def __init__(self, records: list[SourceRecord] | None = None) -> None:
        self.records = {}
        self.aliases = {}
        for record in records or []:
            self.add(record)

    def add(self, record: SourceRecord) -> SourceRecord:
        record.content_hash = record.content_hash or content_hash(record.excerpt)
        normalized = normalize_url(record.url)
        duplicate = next(
            (
                existing
                for existing in self.records.values()
                if (normalized and normalize_url(existing.url) == normalized)
                or existing.content_hash == record.content_hash
            ),
            None,
        )
        if duplicate:
            self.aliases[record.source_id] = duplicate.source_id
            duplicate.retrieved_by = sorted(set(duplicate.retrieved_by + record.retrieved_by))
            duplicate.used_by = sorted(set(duplicate.used_by + record.used_by))
            duplicate.safety_flags = sorted(set(duplicate.safety_flags + record.safety_flags))
            duplicate.supports_claim_ids = sorted(
                set(duplicate.supports_claim_ids + record.supports_claim_ids)
            )
            duplicate.contradicts_claim_ids = sorted(
                set(duplicate.contradicts_claim_ids + record.contradicts_claim_ids)
            )
            return duplicate
        self.records[record.source_id] = record
        self.aliases.setdefault(record.source_id, record.source_id)
        return record

    def get(self, source_id: str) -> SourceRecord | None:
        return self.records.get(source_id)

    def ids(self) -> set[str]:
        return set(self.records)

    def resolve_id(self, source_id: str) -> str:
        """Return the canonical ID retained after URL/content deduplication."""

        return self.aliases.get(source_id, source_id)

    def values(self) -> list[SourceRecord]:
        return list(self.records.values())

    def markdown(self) -> str:
        lines = [
            "# Source ledger",
            "",
            "Sources are normalized research records. Synthetic fixtures are not verified live sources.",
            "",
        ]
        for record in sorted(self.records.values(), key=lambda item: item.source_id):
            anchor = record.source_id.lower().replace("_", "-")
            lines.extend([f"### {record.source_id} — {record.title} {{#{anchor}}}", ""])
            lines.append(f"- **Tier:** {record.tier} ({record.source_type.value})")
            lines.append(f"- **Publisher:** {record.publisher or 'not recorded'}")
            lines.append(f"- **Publication date:** {record.publication_date or 'not recorded'}")
            lines.append(f"- **Access date:** {record.access_date}")
            lines.append(f"- **Jurisdiction:** {record.jurisdiction or 'not recorded'}")
            lines.append(f"- **Synthetic fixture:** {'yes' if record.synthetic else 'no'}")
            lines.append(f"- **URL:** {record.url or 'not recorded'}")
            if record.safety_flags:
                lines.append(f"- **Safety flags:** {', '.join(record.safety_flags)}")
            lines.extend(["", f"> {record.excerpt}", ""])
        return "\n".join(lines)


@dataclass
class ValidationIssue:
    code: str
    message: str
    target_type: str
    target_id: str
    section_id: str | None = None


@dataclass
class ValidationReport:
    errors: list[str]
    warnings: list[str]
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_claim_references(
    claims: list[EvidenceClaim], ledger: SourceLedger
) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    known = ledger.ids()
    for claim in claims:
        claim.supporting_source_ids = [
            ledger.resolve_id(source_id) for source_id in claim.supporting_source_ids
        ]
        claim.contradicting_source_ids = [
            ledger.resolve_id(source_id) for source_id in claim.contradicting_source_ids
        ]
        refs = set(claim.supporting_source_ids + claim.contradicting_source_ids)
        missing = refs - known
        if missing:
            errors.append(f"{claim.claim_id} cites nonexistent sources: {sorted(missing)}")
        if claim.claim_type.value in {"fact", "estimate", "forecast"} and not refs:
            errors.append(f"{claim.claim_id} is factual/quantitative but has no sources")
        if claim.claim_type.value == "synthesis" and claim.confidence > 0.85:
            warnings.append(f"{claim.claim_id} has unusually high synthesis confidence")
    return ValidationReport(errors, warnings)


def validate_country_comparisons(
    comparisons: list[CountryComparison], ledger: SourceLedger
) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    known = ledger.ids()
    for comparison in comparisons:
        comparison.source_ids = [ledger.resolve_id(source_id) for source_id in comparison.source_ids]
        missing = set(comparison.source_ids) - known
        if missing:
            errors.append(
                f"country comparison {comparison.country} cites nonexistent sources: {sorted(missing)}"
            )
        if not comparison.institutional_differences:
            errors.append(
                f"country comparison {comparison.country} must identify institutional differences"
            )
        if comparison.transferability.strip() == "":
            warnings.append(f"country comparison {comparison.country} has no transferability caveat")
    return ValidationReport(errors, warnings)


def validate_report(report: DraftReport, ledger: SourceLedger) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    issues: list[ValidationIssue] = []

    def add_error(
        code: str,
        message: str,
        target_type: str,
        target_id: str,
        section_id: str | None = None,
    ) -> None:
        errors.append(message)
        issues.append(
            ValidationIssue(
                code=code,
                message=message,
                target_type=target_type,
                target_id=target_id,
                section_id=section_id,
            )
        )

    sections = getattr(report, "sections", [])
    section_ids = {section.section_id for section in sections}
    if not sections:
        add_error(
            "report.sections.empty",
            "report must contain at least one section",
            "report",
            report.report_id,
        )
    if len(section_ids) != len(sections):
        add_error(
            "report.sections.duplicate_ids",
            "report section IDs must be unique",
            "report",
            report.report_id,
        )
    if not report.executive_summary_withheld and not report.executive_summary.strip():
        add_error(
            "report.executive_summary.empty",
            "report executive summary must not be empty",
            "executive_summary",
            "executive_summary",
        )
    if not report.decision_matrix_withheld and (
        not report.decision_matrix.criteria or not report.decision_matrix.options
    ):
        add_error(
            "report.decision_matrix.empty",
            "report decision matrix must contain criteria and options",
            "decision_matrix",
            "decision_matrix",
            "decision_matrix",
        )
    cited: list[str] = []
    for section in sections:
        for paragraph in section.paragraphs:
            paragraph.citation_ids = [
                ledger.resolve_id(source_id) for source_id in paragraph.citation_ids
            ]
            cited.extend(paragraph.citation_ids)
            if paragraph.withheld:
                continue
            if paragraph.substantive and not paragraph.citation_ids:
                add_error(
                    "report.paragraph.missing_citation",
                    f"substantive paragraph {paragraph.paragraph_id} has no citation",
                    "paragraph",
                    paragraph.paragraph_id,
                    section.section_id,
                )
            missing = set(paragraph.citation_ids) - ledger.ids()
            if missing:
                add_error(
                    "report.paragraph.invalid_citation",
                    f"paragraph {paragraph.paragraph_id} cites nonexistent sources: {sorted(missing)}",
                    "paragraph",
                    paragraph.paragraph_id,
                    section.section_id,
                )
    if len(cited) != len(set(cited)) and len(cited) > 0:
        warnings.append("some sources are cited repeatedly; this is not itself an error")
    unused = ledger.ids() - set(cited)
    if unused:
        warnings.append(f"sources listed but never cited: {sorted(unused)}")
    source_urls = [record.url.rstrip("/").lower() for record in ledger.values() if record.url]
    duplicates = {url for url in source_urls if source_urls.count(url) > 1}
    if duplicates:
        add_error(
            "report.sources.duplicate_urls",
            f"duplicate source URLs: {sorted(duplicates)}",
            "source_ledger",
            "sources",
            "sources",
        )
    option_ids = {option.option_id for option in report.decision_matrix.options}
    for option in report.decision_matrix.options:
        option.source_ids = [ledger.resolve_id(source_id) for source_id in option.source_ids]
        missing = set(option.source_ids) - ledger.ids()
        if not report.decision_matrix_withheld and missing:
            add_error(
                "report.decision_matrix.invalid_citation",
                f"decision matrix option {option.option_id} cites nonexistent sources: {sorted(missing)}",
                "decision_matrix",
                "decision_matrix",
                "decision_matrix",
            )
    if not report.decision_matrix_withheld and set(report.decision_matrix.scores) != option_ids:
        add_error(
            "report.decision_matrix.incomplete_scores",
            "decision matrix does not include every policy option",
            "decision_matrix",
            "decision_matrix",
            "decision_matrix",
        )
    return ValidationReport(errors, warnings, issues)


def citation_link(source_id: str) -> str:
    anchor = re.sub(r"[^a-z0-9-]", "-", source_id.lower())
    return f"[{source_id}](sources.md#{anchor})"
