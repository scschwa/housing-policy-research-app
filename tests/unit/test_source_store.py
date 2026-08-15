from datetime import date
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

from housing_policy_agents.models import (
    BranchName,
    ClaimType,
    CountryComparison,
    DecisionCriterion,
    DecisionMatrix,
    DraftReport,
    EvidenceClaim,
    EvidenceStrength,
    PolicyOption,
    ReportParagraph,
    ReportSection,
    SearchQuery,
    SourceRecord,
    SourceTier,
    SourceType,
)
from housing_policy_agents.tools.research import ResearchCache
from housing_policy_agents.tools.source_store import (
    SourceLedger,
    validate_claim_references,
    validate_country_comparisons,
    validate_report,
)


def source(source_id: str, url: str) -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        title=source_id,
        url=url,
        source_type=SourceType.SYNTHETIC_FIXTURE,
        tier=SourceTier.AUTHORITATIVE_PRIMARY,
        synthetic=True,
        access_date=date.today(),
    )


def test_ledger_deduplicates_urls_and_merges_provenance() -> None:
    ledger = SourceLedger([source("S-1", "https://fixture.invalid/a")])
    duplicate = source("S-2", "https://fixture.invalid/a/")
    duplicate.retrieved_by = ["branch-b"]
    record = ledger.add(duplicate)
    assert record.source_id == "S-1"
    assert record.retrieved_by == ["branch-b"]
    assert ledger.resolve_id("S-2") == "S-1"
    assert len(ledger.values()) == 1


def test_claim_reference_validation_reports_missing_source() -> None:
    claim = EvidenceClaim(
        text="claim",
        claim_type=ClaimType.FACT,
        evidence_strength=EvidenceStrength.STRONG,
        confidence=0.8,
        originating_agent="test",
        supporting_source_ids=["S-missing"],
    )
    report = validate_claim_references([claim], SourceLedger())
    assert not report.ok
    assert "S-missing" in report.errors[0]


def test_claim_validation_resolves_a_duplicate_source_alias() -> None:
    ledger = SourceLedger([source("S-1", "https://fixture.invalid/a")])
    ledger.add(source("S-2", "https://fixture.invalid/a/"))
    claim = EvidenceClaim(
        text="claim",
        claim_type=ClaimType.FACT,
        evidence_strength=EvidenceStrength.STRONG,
        confidence=0.8,
        originating_agent="test",
        supporting_source_ids=["S-2"],
    )

    report = validate_claim_references([claim], ledger)

    assert report.ok
    assert claim.supporting_source_ids == ["S-1"]


def test_country_comparison_validation_requires_known_sources_and_differences() -> None:
    comparison = CountryComparison(
        country="Testland",
        comparator_reason="test",
        government_level="national",
        policy_design="test",
        eligibility="test",
        funding="test",
        risk_allocation="test",
        administration="test",
        outcomes="test",
        institutional_differences=["different law"],
        transferability="weak",
        evidence_quality=EvidenceStrength.MODERATE,
        source_ids=["S-missing"],
    )
    report = validate_country_comparisons([comparison], SourceLedger())
    assert not report.ok
    assert "S-missing" in report.errors[0]


def test_report_validation_accepts_live_style_section_ids() -> None:
    ledger = SourceLedger([source("S-1", "https://fixture.invalid/report")])
    report = DraftReport(
        title="Live report",
        executive_summary="A concise summary.",
        sections=[
            ReportSection(
                section_id="sec-1",
                title="Live section",
                paragraphs=[ReportParagraph(text="Supported claim.", citation_ids=["S-1"])],
            )
        ],
        decision_matrix=DecisionMatrix(
            criteria=[
                DecisionCriterion(
                    criterion_id="benefit", name="Benefit", description="Benefit"
                )
            ],
            options=[
                PolicyOption(
                    option_id="O1",
                    name="O1",
                    description="demo",
                    mechanism="demo",
                    evidence_strength=EvidenceStrength.MODERATE,
                )
            ],
            scores={"O1": {"benefit": 4}},
        ),
    )

    validation = validate_report(report, ledger)

    assert validation.ok


def test_research_cache_round_trips_sources() -> None:
    cache = ResearchCache(Path("work") / f"cache-test-{uuid4().hex}")
    query = SearchQuery(
        text="mortgage portability policy",
        purpose="baseline",
        branch=BranchName.GOVERNMENT,
    )
    records = [source("S-cache", "https://fixture.invalid/cache")]

    try:
        cache.save(query, records)

        loaded = cache.load(query)
        assert loaded is not None
        assert loaded[0].source_id == "S-cache"
    finally:
        rmtree(cache.root)
