"""Report synthesis and bounded revision."""

from __future__ import annotations

import json
from collections.abc import Iterable

from ..context import RunContext
from ..models import (
    AdversarialReview,
    DecisionCriterion,
    DecisionMatrix,
    DraftReport,
    EvidenceStrength,
    ManagerSynthesis,
    PolicyOption,
    ReportParagraph,
    ReportSection,
    ResearchBrief,
)
from .factory import build_writer_agent


def _paragraph(
    text: str, citations: Iterable[str], *, revision_note: str | None = None
) -> ReportParagraph:
    return ReportParagraph(
        text=text, citation_ids=list(dict.fromkeys(citations)), revision_note=revision_note
    )


def build_policy_options() -> list[PolicyOption]:
    return [
        PolicyOption(
            option_id="O1",
            name="Broad borrower portability",
            description="Allow qualifying borrowers to transfer the existing mortgage to a newly purchased primary residence.",
            mechanism="A contract or program rider follows the borrower while collateral is replaced under defined eligibility and underwriting rules.",
            expected_benefits=["greater mobility", "less lock-in for existing qualifying owners"],
            expected_costs=[
                "complex collateral and servicing operations",
                "repricing or cross-subsidy pressure",
            ],
            risks=["adverse selection", "prepayment and duration repricing", "uneven access"],
            mitigants=[
                "loan-to-value limits",
                "underwriting refresh",
                "capital and guarantee pricing adjustments",
            ],
            implementation_requirements=[
                "statutory or program authority",
                "investor and servicing rule changes",
                "clear consumer disclosures",
            ],
            evidence_strength=EvidenceStrength.MODERATE,
            source_ids=["S-001", "S-002", "S-003", "S-004"],
        ),
        PolicyOption(
            option_id="O2",
            name="Targeted agency-backed pilot",
            description="Test portability for a narrow set of primary-residence loans with public reporting and sunset conditions.",
            mechanism="Use a bounded pilot with explicit eligibility, risk-sharing, reporting, and evaluation requirements.",
            expected_benefits=[
                "learn before scaling",
                "limit initial exposure",
                "focus on documented lock-in cases",
            ],
            expected_costs=["administrative burden", "pilot selection effects", "limited reach"],
            risks=[
                "pilot may not generalize",
                "operational failure",
                "political pressure to expand",
            ],
            mitigants=[
                "independent evaluation",
                "sunset and renewal criteria",
                "transparent loss accounting",
            ],
            implementation_requirements=[
                "agency authority",
                "appropriations or guarantee framework",
                "data collection",
            ],
            evidence_strength=EvidenceStrength.MODERATE,
            source_ids=["S-002", "S-003", "S-004", "S-006"],
        ),
        PolicyOption(
            option_id="O3",
            name="Mobility alternatives without portability",
            description="Address lock-in through assumability, refinancing, transaction-cost support, housing supply, or targeted mobility assistance.",
            mechanism="Use policies that target the mobility constraint without transferring the original loan across collateral.",
            expected_benefits=[
                "potentially lower contract and valuation complexity",
                "more targeted distributional design",
            ],
            expected_costs=[
                "may not preserve the full value of a low-rate loan",
                "requires separate program design",
            ],
            risks=["smaller mobility effect", "fragmented policy response", "uncertain take-up"],
            mitigants=[
                "compare alternatives using common outcome metrics",
                "target assistance to documented barriers",
            ],
            implementation_requirements=[
                "program-specific authority",
                "consumer protection",
                "evaluation",
            ],
            evidence_strength=EvidenceStrength.WEAK,
            source_ids=["S-005", "S-006"],
        ),
    ]


def build_decision_matrix() -> DecisionMatrix:
    criteria = [
        DecisionCriterion(
            criterion_id="consumer_benefit",
            name="Consumer benefit",
            description="Likely direct benefit to affected households",
        ),
        DecisionCriterion(
            criterion_id="access_equity",
            name="Access and equity",
            description="Distribution across owners, non-owners, and underserved groups",
        ),
        DecisionCriterion(
            criterion_id="legal_feasibility",
            name="Legal feasibility",
            description="Authority and litigation uncertainty",
        ),
        DecisionCriterion(
            criterion_id="administrative_complexity",
            name="Administrative complexity",
            description="Operational and implementation burden",
        ),
        DecisionCriterion(
            criterion_id="market_disruption",
            name="Market disruption",
            description="Effect on mortgage and housing market functioning",
        ),
        DecisionCriterion(
            criterion_id="credit_risk",
            name="Credit risk",
            description="Borrower, collateral, and guarantee risk",
        ),
        DecisionCriterion(
            criterion_id="fiscal_exposure",
            name="Fiscal or taxpayer exposure",
            description="Potential public cost or contingent liability",
        ),
        DecisionCriterion(
            criterion_id="financial_stability",
            name="Financial stability",
            description="Systemic and liquidity implications",
        ),
        DecisionCriterion(
            criterion_id="speed",
            name="Speed of implementation",
            description="Time to implement responsibly",
        ),
        DecisionCriterion(
            criterion_id="evidence_strength",
            name="Evidence strength",
            description="Strength of available evidence",
        ),
        DecisionCriterion(
            criterion_id="reversibility",
            name="Reversibility",
            description="Ability to correct or unwind the design",
        ),
    ]
    scores = {
        "O1": {
            criterion.criterion_id: value
            for criterion, value in zip(
                criteria, ["5", "2", "2", "1", "1", "2", "2", "2", "1", "3", "1"], strict=True
            )
        },
        "O2": {
            criterion.criterion_id: value
            for criterion, value in zip(
                criteria, ["3", "3", "4", "2", "3", "3", "3", "3", "2", "3", "4"], strict=True
            )
        },
        "O3": {
            criterion.criterion_id: value
            for criterion, value in zip(
                criteria, ["2", "4", "4", "4", "4", "4", "4", "4", "3", "2", "4"], strict=True
            )
        },
    }
    return DecisionMatrix(
        criteria=criteria,
        options=build_policy_options(),
        scores=scores,
        caveats=[
            "Scores are qualitative synthesis, not a forecast or a substitute for calibrated analysis.",
            "A higher score is not uniformly better; complexity, exposure, and risk criteria should be interpreted separately.",
        ],
    )


def offline_report(
    brief: ResearchBrief,
    managers: list[ManagerSynthesis],
    source_ids: set[str],
    revised: bool = False,
) -> DraftReport:
    title = "Mortgage portability: policy designs, effects, barriers, and risks"
    sections = [
        ReportSection(
            "executive_summary",
            "Executive summary",
            [
                _paragraph(
                    "Mortgage portability could reduce lock-in for some existing borrowers, but its value would depend on contract authority, collateral substitution, servicing capacity, risk-transfer design, and distributional safeguards.",
                    ["S-001", "S-002", "S-003", "S-004"],
                )
            ],
        ),
        ReportSection(
            "question_scope",
            "User question and policy scope",
            [
                _paragraph(
                    f"This report evaluates the proposed policy in the United States for primary residences, with attention to consumer effects, legal and operational barriers, financial risk, distribution, and international precedents. The working audience is {brief.audience}.",
                    ["S-001", "S-002"],
                )
            ],
        ),
        ReportSection(
            "us_baseline",
            "Current U.S. baseline",
            [
                _paragraph(
                    "The fixture baseline treats a conventional mortgage as linked to a particular property, so borrower portability would require changes to contracts, program rules, investor expectations, and collateral controls.",
                    ["S-001"],
                )
            ],
        ),
        ReportSection(
            "policy_mechanisms",
            "Policy mechanisms or options",
            [
                _paragraph(
                    "Three designs are compared: broad portability, a targeted agency-backed pilot, and mobility alternatives that do not transfer the original mortgage across collateral.",
                    ["S-001", "S-002", "S-005", "S-006"],
                )
            ],
        ),
        ReportSection(
            "evidence_domains",
            "Evidence by research domain",
            [
                _paragraph(
                    "Government and legal materials emphasize authority and program structure; servicing evidence emphasizes operational change; finance evidence emphasizes prepayment and valuation; external research provides plausible but uncertain mobility and distributional effects.",
                    ["S-001", "S-002", "S-003", "S-004", "S-005", "S-006"],
                )
            ],
        ),
        ReportSection(
            "stakeholder_effects",
            "Stakeholder effects",
            [
                _paragraph(
                    "Existing qualifying borrowers may gain mobility, while lenders, servicers, investors, and guarantors would bear new underwriting, operational, valuation, and risk-allocation requirements.",
                    ["S-003", "S-004", "S-005", "S-006"],
                )
            ],
        ),
        ReportSection(
            "distributional_equity",
            "Distributional and equity considerations",
            [
                _paragraph(
                    "Benefits may be concentrated among current owners who can qualify for a move; non-owners and households with limited access to credit may receive fewer direct benefits and could experience indirect price or allocation effects.",
                    ["S-005", "S-006"],
                )
            ],
        ),
        ReportSection(
            "legal_implementation",
            "Legal and implementation considerations",
            [
                _paragraph(
                    "The material legal questions concern statutory authority, rulemaking, federal-state boundaries, securitization documents, disclosures, collateral substitution, and litigation risk. These are unresolved questions for formal legal analysis, not definitive legal conclusions.",
                    ["S-002", "S-003"],
                )
            ],
        ),
        ReportSection(
            "international_comparisons",
            "International comparisons",
            [
                _paragraph(
                    "The United Kingdom, Canada, and Denmark offer design lessons, but differences in refinancing, bond funding, insurance, legal structure, and administration make direct transplantation weak.",
                    ["S-007", "S-008", "S-009"],
                )
            ],
        ),
        ReportSection(
            "financial_credit_fiscal_risk",
            "Financial, credit, fiscal, and systemic-risk considerations",
            [
                _paragraph(
                    "Portable low-rate loans could change expected prepayment, duration, mortgage-backed-security valuation, guarantee pricing, and public risk exposure; the direction and magnitude depend on eligibility and loss allocation.",
                    ["S-002", "S-004", "S-006"],
                )
            ],
        ),
        ReportSection(
            "arguments_for_against",
            "Key arguments for and against",
            [
                _paragraph(
                    "The strongest argument for portability is reduced lock-in and improved mobility for eligible existing borrowers. The strongest arguments against broad portability are operational complexity, adverse selection, uneven access, and uncertain effects on risk transfer.",
                    ["S-003", "S-004", "S-005", "S-006"],
                ),
                _paragraph(
                    "A weak anecdotal fixture source claims that portability would solve every affordability and mobility problem; it has no methodology and should not support a strong conclusion.",
                    ["S-011"],
                ),
            ],
        ),
        ReportSection(
            "agreement_disagreement",
            "Areas of agreement and disagreement",
            [
                _paragraph(
                    "The branches agree that mobility benefits are plausible and that implementation would be complex. They disagree about the scale of benefits, who would receive them, and whether a narrow pilot could contain market and taxpayer risks.",
                    ["S-003", "S-004", "S-005", "S-006"],
                )
            ],
        ),
        ReportSection(
            "evidence_gaps",
            "Evidence gaps and uncertainties",
            [
                _paragraph(
                    "Key gaps include causal estimates of lock-in, calibrated distributional effects, investor pricing, servicing capacity, legal authority, and stress outcomes under downturns or rate shocks.",
                    ["S-002", "S-003", "S-004", "S-006"],
                )
            ],
        ),
        ReportSection(
            "design_choices_mitigants",
            "Policy design choices and mitigants",
            [
                _paragraph(
                    "A responsible design would use narrow eligibility, collateral and affordability tests, transparent risk pricing, servicing standards, public loss accounting, independent evaluation, and sunset criteria.",
                    ["S-002", "S-003", "S-004", "S-006"],
                )
            ],
        ),
        ReportSection(
            "decision_matrix",
            "Decision matrix",
            [
                _paragraph(
                    "The matrix below compares alternatives qualitatively across consumer, legal, operational, market, risk, fiscal, evidence, and reversibility dimensions.",
                    ["S-001", "S-002", "S-003", "S-004", "S-005", "S-006"],
                )
            ],
        ),
        ReportSection(
            "conclusions",
            "Conclusions",
            [
                _paragraph(
                    "The evidence supports a conditional conclusion: a targeted, measurable pilot may be more defensible than broad portability if policymakers value mobility gains and can establish authority, risk controls, and distributional safeguards. The fixture does not support an unconditional recommendation.",
                    ["S-002", "S-003", "S-004", "S-005", "S-006"],
                )
            ],
        ),
        ReportSection(
            "sources",
            "Sources",
            [
                _paragraph(
                    "Source records are listed in the companion source ledger. Synthetic records are explicitly labeled and are included only to exercise the evaluation and safety workflow.",
                    ["S-001"],
                )
            ],
        ),
    ]
    # Ablation runs may intentionally omit a research branch. Keep the report
    # structurally valid while ensuring it never cites a source absent from the
    # normalized ledger. The fallback citation supports only the existence of
    # the limitation, not the omitted domain's substantive conclusion.
    fallback = next(iter(sorted(source_ids)), None)
    for section in sections:
        for paragraph in section.paragraphs:
            paragraph.citation_ids = [
                source_id for source_id in paragraph.citation_ids if source_id in source_ids
            ]
            if paragraph.substantive and not paragraph.citation_ids and fallback:
                paragraph.citation_ids = [fallback]
    return DraftReport(
        title=title,
        executive_summary="Portability could reduce lock-in for some borrowers, but broad implementation creates legal, servicing, valuation, distributional, and taxpayer-risk questions.",
        sections=sections,
        decision_matrix=build_decision_matrix(),
        source_ids_used=sorted(source_ids),
        evidence_gaps=[
            "No calibrated causal estimate",
            "No verified live legal or market data in this offline fixture",
            "No stress-tested fiscal estimate",
        ],
        limitations=[
            "Synthetic fixture only",
            "International comparisons are illustrative and institutionally imperfect",
        ],
        revised=revised,
        revision_count=1 if revised else 0,
    )


async def write_report(
    brief: ResearchBrief,
    managers: list[ManagerSynthesis],
    source_ids: set[str],
    context: RunContext,
) -> DraftReport:
    if context.config.research_provider == "offline":
        return offline_report(brief, managers, source_ids)
    from agents import RunConfig, Runner

    agent = build_writer_agent(context.config)
    result = await Runner.run(
        agent,
        json.dumps(
            {
                "brief": brief.model_dump(mode="json"),
                "manager_syntheses": [item.model_dump(mode="json") for item in managers],
                "source_ids": sorted(source_ids),
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
    if not isinstance(result.final_output, DraftReport):
        raise TypeError("writer did not return DraftReport")
    return result.final_output


async def revise_report(
    report: DraftReport, review: AdversarialReview, context: RunContext
) -> DraftReport:
    if context.config.research_provider == "offline":
        for section in report.sections:
            if section.section_id == "arguments_for_against":
                section.paragraphs = [
                    item
                    for item in section.paragraphs
                    if "weak anecdotal fixture source" not in item.text
                ]
                section.paragraphs.append(
                    _paragraph(
                        "The remaining evidence supports only a conditional mobility benefit; anecdotal claims are not used to establish affordability or universal impact.",
                        ["S-005", "S-006"],
                        revision_note="Removed an unsupported anecdotal claim identified by adversarial review.",
                    )
                )
        report.revised = True
        report.revision_count += 1
        return report
    from agents import RunConfig, Runner

    agent = build_writer_agent(context.config)
    result = await Runner.run(
        agent,
        json.dumps(
            {"draft": report.model_dump(mode="json"), "review": review.model_dump(mode="json")},
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
    if not isinstance(result.final_output, DraftReport):
        raise TypeError("revision writer did not return DraftReport")
    revised = result.final_output
    revised.revised = True
    revised.revision_count = report.revision_count + 1
    return revised
