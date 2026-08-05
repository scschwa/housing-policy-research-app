"""Independent adversarial review."""

from __future__ import annotations

import json

from ..context import RunContext
from ..models import AdversarialReview, DraftReport, ReleaseRecommendation, ReviewFinding
from ..tools.source_store import SourceLedger, validate_report
from .factory import build_reviewer_agent


def offline_review(report: DraftReport, ledger: SourceLedger) -> AdversarialReview:
    validation = validate_report(report, ledger)
    findings: list[ReviewFinding] = []
    for error in validation.errors:
        findings.append(
            ReviewFinding(
                severity="critical",
                affected_section="deterministic validation",
                disputed_claim=error,
                explanation=error,
                recommended_correction="Correct the structured report before release.",
                mandatory_revision=True,
            )
        )
    for section in report.sections:
        for paragraph in section.paragraphs:
            weak_sources = [
                record.source_id
                for record in ledger.values()
                if record.source_id in paragraph.citation_ids and record.tier >= 5
            ]
            if weak_sources:
                findings.append(
                    ReviewFinding(
                        severity="major",
                        affected_section=section.title,
                        disputed_claim=paragraph.text,
                        explanation=f"The paragraph cites weak or unverified source(s) {weak_sources}; they should not support a strong conclusion.",
                        evidence_involved=weak_sources,
                        recommended_correction="Remove the weak source from the evidentiary basis and qualify the statement.",
                        mandatory_revision=True,
                    )
                )
    for record in ledger.values():
        if record.safety_flags:
            findings.append(
                ReviewFinding(
                    severity="security",
                    affected_section="source ledger",
                    disputed_claim=record.source_id,
                    explanation="Retrieved content contains prompt-injection text and must remain untrusted data.",
                    evidence_involved=[record.source_id],
                    recommended_correction="Retain the source for auditability but exclude it from substantive support.",
                    mandatory_revision=False,
                )
            )
    mandatory = any(item.mandatory_revision for item in findings)
    return AdversarialReview(
        findings=findings,
        citation_completeness=0.0 if validation.errors else 1.0,
        grounding_score=4.0 if not validation.errors else 2.5,
        balance_score=4.0,
        calibration_score=4.0,
        security_score=5.0 if any(item.severity == "security" for item in findings) else 4.0,
        release_recommendation=ReleaseRecommendation.REVISE
        if mandatory
        else ReleaseRecommendation.APPROVE_WITH_CAVEATS,
        reviewer_notes=validation.warnings,
    )


async def review_report(
    report: DraftReport, ledger: SourceLedger, evidence: object, context: RunContext
) -> AdversarialReview:
    if context.config.research_provider == "offline":
        return offline_review(report, ledger)
    from agents import RunConfig, Runner

    agent = build_reviewer_agent(context.config)
    result = await Runner.run(
        agent,
        json.dumps(
            {
                "draft": report.model_dump(mode="json"),
                "sources": [item.model_dump(mode="json") for item in ledger.values()],
                "evidence": evidence,
            },
            indent=2,
        ),
        max_turns=context.config.max_turns_per_agent,
        run_config=RunConfig(
            model=context.config.openai_model,
            workflow_name="Housing Policy Research Network",
            trace_id=context.trace_id,
            trace_include_sensitive_data=context.config.trace_include_sensitive_data,
        ),
    )
    if not isinstance(result.final_output, AdversarialReview):
        raise TypeError("reviewer did not return AdversarialReview")
    return result.final_output
