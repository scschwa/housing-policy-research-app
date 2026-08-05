"""Specialist execution, including deterministic fixture behavior."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from ..config import AppConfig
from ..context import RunContext
from ..guardrails import inspect_untrusted_text
from ..models import (
    BranchName,
    BranchStatus,
    ClaimType,
    Contradiction,
    EvidenceClaim,
    EvidenceStrength,
    ResearchAssignment,
    SpecialistFinding,
    SourceRecord,
)
from ..tools.research import FixtureResearchBackend, LiveResearchBackend, ResearchBackend
from .factory import build_specialist_agent


SPECIALIST_MANAGER: dict[BranchName, str] = {
    BranchName.GOVERNMENT: "policy_research_manager",
    BranchName.LEGAL: "policy_research_manager",
    BranchName.ACADEMIC: "policy_research_manager",
    BranchName.CONSUMER: "industry_research_manager",
    BranchName.ORIGINATOR: "industry_research_manager",
    BranchName.SERVICING: "industry_research_manager",
    BranchName.RISK_TRANSFER: "industry_research_manager",
    BranchName.GENERAL_ADVOCACY: "advocacy_research_manager",
    BranchName.DISADVANTAGED_COMMUNITIES: "advocacy_research_manager",
    BranchName.FINANCIAL_SUSTAINABILITY: "advocacy_research_manager",
    BranchName.GLOBAL: "global_research_manager",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _claim(branch: BranchName, text: str, claim_type: ClaimType, sources: list[str], strength: EvidenceStrength, confidence: float, limitations: list[str]) -> EvidenceClaim:
    return EvidenceClaim(
        text=text,
        claim_type=claim_type,
        supporting_source_ids=sources,
        evidence_strength=strength,
        confidence=confidence,
        geographic_scope="United States",
        applicable_period="fixture scenario period",
        material_limitations=limitations,
        originating_agent=branch.value,
    )


def deterministic_claims(branch: BranchName) -> tuple[list[EvidenceClaim], list[Contradiction], str]:
    limitations = ["Synthetic evaluation fixture; not live verified evidence."]
    if branch == BranchName.GOVERNMENT:
        claims = [
            _claim(branch, "The fixture baseline treats mortgage portability as a material change to property-linked contract and program structures.", ClaimType.FACT, ["S-001"], EvidenceStrength.STRONG, 0.93, limitations),
            _claim(branch, "A policy would likely require explicit statutory, programmatic, or rulemaking authority rather than relying on an unstated administrative assumption.", ClaimType.INTERPRETATION, ["S-002"], EvidenceStrength.MODERATE, 0.80, limitations),
        ]
        return claims, [], "Government analysis highlights baseline contract structure and authority questions."
    if branch == BranchName.LEGAL:
        claim = _claim(branch, "Portability would raise unresolved questions about statutory authority, securitization documents, collateral substitution, disclosures, and federal-state implementation boundaries.", ClaimType.INTERPRETATION, ["S-002", "S-003"], EvidenceStrength.MODERATE, 0.78, limitations)
        return [claim], [], "The legal issue is material but should be framed as a question for formal legal analysis, not a definitive conclusion."
    if branch == BranchName.ACADEMIC:
        claims = [
            _claim(branch, "The fixture mobility evidence suggests that low-rate lock-in can affect household relocation decisions, but the survey does not establish a causal policy effect.", ClaimType.ESTIMATE, ["S-005"], EvidenceStrength.MODERATE, 0.72, limitations),
            _claim(branch, "A modeled distributional result suggests direct benefits may accrue more to existing qualifying owners than to households without an existing low-rate mortgage.", ClaimType.ESTIMATE, ["S-006"], EvidenceStrength.MODERATE, 0.74, limitations),
        ]
        contradiction = Contradiction(claim_id=claims[0].claim_id, supporting_source_ids=["S-005"], contradicting_source_ids=["S-011"], description="The anecdotal source asserts universal benefits without a method; it does not provide reliable contrary evidence.")
        return claims, [contradiction], "External evidence supports a plausible mobility benefit but does not support false precision."
    if branch == BranchName.CONSUMER:
        return [_claim(branch, "Consumers who already hold a low-rate mortgage may gain mobility, while non-borrowers and households unable to qualify for a new property may receive fewer direct benefits.", ClaimType.SYNTHESIS, ["S-005", "S-006"], EvidenceStrength.MODERATE, 0.76, limitations)], [], "Consumer effects are heterogeneous and depend on eligibility, price responses, and the ability to move."
    if branch == BranchName.ORIGINATOR:
        return [_claim(branch, "Originators would need underwriting and operational rules for the new property, collateral, affordability, compliance, and repurchase allocation.", ClaimType.INTERPRETATION, ["S-001", "S-003"], EvidenceStrength.MODERATE, 0.76, limitations)], [], "Operational and compliance costs could vary by channel and product type."
    if branch == BranchName.SERVICING:
        return [_claim(branch, "Servicers would face material boarding, escrow, lien-release, insurance, communication, and transfer complexity when a loan follows a borrower to a different property.", ClaimType.FACT, ["S-003"], EvidenceStrength.STRONG, 0.88, limitations)], [], "The fixture does not quantify implementation cost or capacity."
    if branch == BranchName.RISK_TRANSFER:
        claims = [
            _claim(branch, "Portable low-rate loans could alter expected prepayment, duration, valuation, guarantee pricing, and interest-rate risk allocation in mortgage finance markets.", ClaimType.FORECAST, ["S-004"], EvidenceStrength.MODERATE, 0.75, limitations),
            _claim(branch, "Taxpayer and credit risk depend on eligibility, collateral substitution, loss allocation, adverse selection, and guarantee design.", ClaimType.SYNTHESIS, ["S-002", "S-004", "S-006"], EvidenceStrength.MODERATE, 0.77, limitations),
        ]
        return claims, [], "Risk effects are design-dependent and should not be reduced to a single cost estimate."
    if branch == BranchName.GENERAL_ADVOCACY:
        return [_claim(branch, "Consumer safeguards would need to address transparency, fees, eligibility complexity, servicing treatment, disputes, and market power.", ClaimType.SYNTHESIS, ["S-003", "S-005"], EvidenceStrength.MODERATE, 0.72, limitations)], [], "Advocacy concerns identify value conflicts as well as implementation safeguards."
    if branch == BranchName.DISADVANTAGED_COMMUNITIES:
        return [_claim(branch, "Distributional effects may differ across first-generation, rural, thin-file, lower-income, and displacement-exposed households; existing owners and non-owners should not be treated as one group.", ClaimType.SYNTHESIS, ["S-005", "S-006"], EvidenceStrength.MODERATE, 0.75, limitations)], [], "The fixture does not model all legally relevant demographic or geographic groups."
    if branch == BranchName.FINANCIAL_SUSTAINABILITY:
        return [_claim(branch, "A durable program would need stress testing for downturns, defaults, rate shocks, adverse selection, fiscal stress, operational failure, and political changes.", ClaimType.SYNTHESIS, ["S-002", "S-004", "S-006"], EvidenceStrength.MODERATE, 0.79, limitations)], [], "Long-run fiscal and systemic outcomes remain uncertain without a calibrated model."
    if branch == BranchName.GLOBAL:
        return [_claim(branch, "International comparators can provide design lessons, but institutional differences in funding, refinancing, legal structure, and administration weaken direct transplantation.", ClaimType.INTERPRETATION, ["S-007", "S-008", "S-009"], EvidenceStrength.MODERATE, 0.82, limitations)], [], "The fixture supplies three comparators but no verified cross-country outcome estimate."
    return [], [], "No fixture claims were configured for this branch."


async def run_specialist(assignment: ResearchAssignment, backend: ResearchBackend, context: RunContext) -> SpecialistFinding:
    started = _now()
    try:
        source_records: list[SourceRecord] = []
        for query in assignment.search_queries:
            source_records.extend(await backend.search(query, assignment))
        deduped = {item.source_id: item for item in source_records}
        if isinstance(backend, FixtureResearchBackend):
            claims, contradictions, summary = deterministic_claims(assignment.branch)
            for source in deduped.values():
                source.retrieved_by = sorted(set(source.retrieved_by + [assignment.branch.value]))
            injection_flags = [source.source_id for source in deduped.values() if inspect_untrusted_text(source.excerpt)]
            # The malicious fixture is retained in the ledger for auditability but never becomes evidence.
            claims = [claim for claim in claims if not any(source_id in injection_flags for source_id in claim.supporting_source_ids)]
            return SpecialistFinding(
                branch=assignment.branch,
                agent_name=f"{assignment.branch.value}_researcher",
                status=BranchStatus.COMPLETED,
                summary=summary,
                claims=claims,
                discovered_sources=list(deduped.values()),
                contradictions=contradictions,
                source_ids=sorted(deduped),
                limitations=["Fixture-backed synthetic evidence; do not present as verified live sources."],
                prompt_injection_flags=injection_flags,
                started_at=started,
                finished_at=_now(),
            )

        from agents import RunConfig, Runner

        agent = build_specialist_agent(assignment.branch.value, context.config, backend.agent_tools())
        run_config = RunConfig(
            model=context.config.openai_model,
            workflow_name="Housing Policy Research Network",
            trace_id=context.trace_id,
            trace_include_sensitive_data=context.config.trace_include_sensitive_data,
            trace_metadata={"run_id": context.run_id, "branch": assignment.branch.value},
        )
        result = await Runner.run(
            agent,
            json.dumps(assignment.model_dump(mode="json"), indent=2),
            max_turns=context.config.max_turns_per_agent,
            run_config=run_config,
        )
        finding = result.final_output
        if not isinstance(finding, SpecialistFinding):
            raise TypeError("specialist did not return SpecialistFinding")
        finding.branch = assignment.branch
        finding.agent_name = f"{assignment.branch.value}_researcher"
        finding.status = BranchStatus.COMPLETED
        finding.started_at = started
        finding.finished_at = _now()
        return finding
    except Exception as exc:  # branch failures are preserved in the final package
        return SpecialistFinding(
            branch=assignment.branch,
            agent_name=f"{assignment.branch.value}_researcher",
            status=BranchStatus.FAILED,
            summary="The branch failed before producing a complete finding.",
            limitations=["This perspective was unavailable for this run."],
            error=f"{type(exc).__name__}: {exc}",
            started_at=started,
            finished_at=_now(),
        )
