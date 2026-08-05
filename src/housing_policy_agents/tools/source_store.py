"""Normalized source ledger and citation reference checks."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

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
class ValidationReport:
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


REQUIRED_SECTION_IDS = [
    "executive_summary",
    "question_scope",
    "us_baseline",
    "policy_mechanisms",
    "evidence_domains",
    "stakeholder_effects",
    "distributional_equity",
    "legal_implementation",
    "international_comparisons",
    "financial_credit_fiscal_risk",
    "arguments_for_against",
    "agreement_disagreement",
    "evidence_gaps",
    "design_choices_mitigants",
    "decision_matrix",
    "conclusions",
    "sources",
]


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
    sections = getattr(report, "sections", [])
    section_ids = {section.section_id for section in sections}
    missing_sections = set(REQUIRED_SECTION_IDS) - section_ids
    if missing_sections:
        errors.append(f"missing required report sections: {sorted(missing_sections)}")
    cited: list[str] = []
    for section in sections:
        for paragraph in section.paragraphs:
            paragraph.citation_ids = [
                ledger.resolve_id(source_id) for source_id in paragraph.citation_ids
            ]
            cited.extend(paragraph.citation_ids)
            if paragraph.substantive and not paragraph.citation_ids:
                errors.append(f"substantive paragraph {paragraph.paragraph_id} has no citation")
            missing = set(paragraph.citation_ids) - ledger.ids()
            if missing:
                errors.append(
                    f"paragraph {paragraph.paragraph_id} cites nonexistent sources: {sorted(missing)}"
                )
    if len(cited) != len(set(cited)) and len(cited) > 0:
        warnings.append("some sources are cited repeatedly; this is not itself an error")
    unused = ledger.ids() - set(cited)
    if unused:
        warnings.append(f"sources listed but never cited: {sorted(unused)}")
    source_urls = [record.url.rstrip("/").lower() for record in ledger.values() if record.url]
    duplicates = {url for url in source_urls if source_urls.count(url) > 1}
    if duplicates:
        errors.append(f"duplicate source URLs: {sorted(duplicates)}")
    option_ids = {option.option_id for option in report.decision_matrix.options}
    if set(report.decision_matrix.scores) != option_ids:
        errors.append("decision matrix does not include every policy option")
    return ValidationReport(errors, warnings)


def citation_link(source_id: str) -> str:
    anchor = re.sub(r"[^a-z0-9-]", "-", source_id.lower())
    return f"[{source_id}](sources.md#{anchor})"
