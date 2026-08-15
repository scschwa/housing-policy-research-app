import asyncio
from datetime import date

from housing_policy_agents.agents.rework import rework_validation_failures
from housing_policy_agents.agents.writer import _contain_report_citations
from housing_policy_agents.config import AppConfig
from housing_policy_agents.context import RunContext
from housing_policy_agents.models import (
    DecisionCriterion,
    DecisionMatrix,
    DraftReport,
    EvidenceStrength,
    PolicyOption,
    RepairStatus,
    ReportAudit,
    ReportParagraph,
    ReportSection,
    SourceRecord,
    SourceTier,
    SourceType,
)
from housing_policy_agents.reporting.render import render_audit_report
from housing_policy_agents.telemetry.interactions import InteractionTelemetry
from housing_policy_agents.tools.source_store import SourceLedger, validate_report


def _report() -> DraftReport:
    return DraftReport(
        title="Validation repair test",
        executive_summary="A supported summary.",
        sections=[
            ReportSection(
                section_id="analysis",
                title="Analysis",
                paragraphs=[
                    ReportParagraph(
                        paragraph_id="repairable",
                        text="This claim has one valid and one invalid citation.",
                        citation_ids=["s1", "missing"],
                    ),
                    ReportParagraph(
                        paragraph_id="unsupported",
                        text="This substantive claim has no evidence.",
                        citation_ids=[],
                    ),
                ],
            )
        ],
        decision_matrix=DecisionMatrix(
            criteria=[
                DecisionCriterion(
                    criterion_id="benefit",
                    name="Benefit",
                    description="Relative expected benefit",
                )
            ],
            options=[
                PolicyOption(
                    option_id="o1",
                    name="Option 1",
                    description="Test option",
                    mechanism="Test mechanism",
                    evidence_strength=EvidenceStrength.MODERATE,
                    source_ids=["s1", "missing-matrix"],
                )
            ],
            scores={"o1": {"benefit": 3}},
        ),
    )


def test_rework_repairs_validatable_unit_and_withholds_unsupported_unit() -> None:
    ledger = SourceLedger(
        [
            SourceRecord(
                source_id="s1",
                title="Test source",
                url="https://fixture.invalid/source",
                source_type=SourceType.SYNTHETIC_FIXTURE,
                tier=SourceTier.AUTHORITATIVE_PRIMARY,
                synthetic=True,
                access_date=date.today(),
            )
        ]
    )
    report = _report()
    validation = validate_report(report, ledger)
    telemetry = InteractionTelemetry(run_id="run-rework-test")
    context = RunContext(
        config=AppConfig(research_provider="offline", max_rework_passes=2),
        run_id="run-rework-test",
        interaction_telemetry=telemetry,
    )

    outcome = asyncio.run(
        rework_validation_failures(
            report=report,
            validation=validation,
            ledger=ledger,
            evidence={},
            context=context,
            stage="pre_review",
        )
    )

    repaired = next(
        paragraph
        for section in outcome.report.sections
        for paragraph in section.paragraphs
        if paragraph.paragraph_id == "repairable"
    )
    withheld = next(
        paragraph
        for section in outcome.report.sections
        for paragraph in section.paragraphs
        if paragraph.paragraph_id == "unsupported"
    )
    statuses = {entry.target_id: entry.status for entry in outcome.entries}

    assert outcome.validation.errors == []
    assert repaired.citation_ids == ["s1"]
    assert repaired.withheld is False
    assert withheld.withheld is True
    assert withheld.substantive is False
    assert "WITHHELD" in withheld.text
    assert outcome.report.decision_matrix.options[0].source_ids == ["s1"]
    assert outcome.report.decision_matrix_withheld is False
    assert statuses["repairable"] == RepairStatus.REPAIRED
    assert statuses["unsupported"] == RepairStatus.WITHHELD
    assert statuses["decision_matrix"] == RepairStatus.REPAIRED
    assert telemetry.interactions[0]["agent"] == "validation_rework_specialist"
    markdown = render_audit_report(
        ReportAudit(
            run_id="run-rework-test",
            entries=outcome.entries,
            repair_passes=outcome.passes,
            initial_error_count=len(validation.errors),
            final_error_count=len(outcome.validation.errors),
        )
    )
    assert "### Original" in markdown
    assert "### Withheld representation" in markdown
    assert "### Final report representation" in markdown
    assert "This substantive claim has no evidence." in markdown
    assert "**withheld**" in markdown


def test_writer_boundary_routes_invalid_citations_to_validation() -> None:
    report = _contain_report_citations(_report(), {"s1"})
    ledger = SourceLedger(
        [
            SourceRecord(
                source_id="s1",
                title="Test source",
                url="https://fixture.invalid/source",
                source_type=SourceType.SYNTHETIC_FIXTURE,
                tier=SourceTier.AUTHORITATIVE_PRIMARY,
                synthetic=True,
                access_date=date.today(),
            )
        ]
    )

    validation = validate_report(report, ledger)

    assert "missing" in report.sections[0].paragraphs[0].citation_ids
    assert "missing-matrix" in report.decision_matrix.options[0].source_ids
    assert {issue.code for issue in validation.issues} >= {
        "report.paragraph.invalid_citation",
        "report.decision_matrix.invalid_citation",
    }
