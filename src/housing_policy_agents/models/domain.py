"""Pydantic models used at all major workflow boundaries."""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import IntEnum, StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class ClaimType(StrEnum):
    FACT = "fact"
    ESTIMATE = "estimate"
    INTERPRETATION = "interpretation"
    FORECAST = "forecast"
    STAKEHOLDER_POSITION = "stakeholder_position"
    SYNTHESIS = "synthesis"


class EvidenceStrength(StrEnum):
    VERY_WEAK = "very_weak"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class SourceTier(IntEnum):
    AUTHORITATIVE_PRIMARY = 1
    OFFICIAL_OR_PEER_REVIEWED = 2
    CREDIBLE_SPECIALIST = 3
    STAKEHOLDER_OR_ADVOCACY = 4
    COMMENTARY_OR_UNVERIFIED = 5


class SourceType(StrEnum):
    STATUTE = "statute"
    REGULATION = "regulation"
    PROPOSED_RULE = "proposed_rule"
    EXECUTIVE_ACTION = "executive_action"
    AGENCY_GUIDANCE = "agency_guidance"
    CONGRESSIONAL_MATERIAL = "congressional_material"
    GOVERNMENT_REPORT = "government_report"
    ADMINISTRATIVE_DATASET = "administrative_dataset"
    COURT_OPINION = "court_opinion"
    OFFICIAL_SPEECH = "official_speech"
    PEER_REVIEWED = "peer_reviewed"
    WORKING_PAPER = "working_paper"
    THINK_TANK = "think_tank"
    ADVOCACY_ANALYSIS = "advocacy_analysis"
    JOURNALISM = "journalism"
    COMMENTARY = "commentary"
    SYNTHETIC_FIXTURE = "synthetic_fixture"


class BranchName(StrEnum):
    GOVERNMENT = "government_sources"
    LEGAL = "legal_regulatory"
    ACADEMIC = "think_tank_academic"
    CONSUMER = "consumer"
    ORIGINATOR = "loan_originator"
    SERVICING = "servicing"
    RISK_TRANSFER = "secondary_market_risk_transfer"
    GENERAL_ADVOCACY = "general_consumer_advocacy"
    DISADVANTAGED_COMMUNITIES = "disadvantaged_communities"
    FINANCIAL_SUSTAINABILITY = "financial_sustainability"
    GLOBAL = "global_research"


class ManagerName(StrEnum):
    POLICY = "policy_research_manager"
    INDUSTRY = "industry_research_manager"
    ADVOCACY = "advocacy_research_manager"
    GLOBAL = "global_research_manager"


class BranchStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNAVAILABLE = "unavailable"


class ReleaseRecommendation(StrEnum):
    APPROVE = "approve"
    APPROVE_WITH_CAVEATS = "approve_with_caveats"
    REVISE = "revise"


class RunMode(StrEnum):
    INTERACTIVE = "interactive"
    FAST = "fast"


class ResearchProviderName(StrEnum):
    OFFLINE = "offline"
    WEB = "web"


class UserResearchRequest(StrictModel):
    request_id: str = Field(default_factory=lambda: f"req-{uuid4().hex[:12]}")
    question: str = Field(min_length=20, max_length=4000)
    audience: str | None = Field(default=None, max_length=300)
    jurisdiction: str = "United States"
    policy_scope: str | None = Field(default=None, max_length=800)
    time_horizon: str | None = Field(default=None, max_length=300)
    stakeholder_perspective: str | None = Field(default=None, max_length=500)
    mode: RunMode = RunMode.INTERACTIVE
    provider: ResearchProviderName = ResearchProviderName.OFFLINE
    accept_defaults: bool = False
    output_formats: list[str] = Field(default_factory=lambda: ["markdown", "json"])

    @field_validator("output_formats")
    @classmethod
    def validate_formats(cls, value: list[str]) -> list[str]:
        allowed = {"markdown", "json"}
        if not value or any(item not in allowed for item in value):
            raise ValueError("output_formats must contain only markdown and/or json")
        return list(dict.fromkeys(value))


class ClarificationQuestion(StrictModel):
    question_id: str
    prompt: str
    rationale: str
    options: list[str] = Field(default_factory=list, max_length=5)
    default: str | None = None
    required: bool = False


class ResearchBrief(StrictModel):
    request_id: str
    question: str
    audience: str
    jurisdiction: str
    policy_scope: str
    time_horizon: str
    stakeholder_perspective: str
    mode: RunMode
    defaults_applied: list[str] = Field(default_factory=list)
    clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)
    safety_disclosures: list[str] = Field(default_factory=list)


class SearchQuery(StrictModel):
    query_id: str = Field(default_factory=lambda: f"q-{uuid4().hex[:10]}")
    text: str = Field(min_length=5, max_length=500)
    purpose: str
    branch: BranchName
    domains: list[str] = Field(default_factory=list)
    date_from: date | None = None
    date_to: date | None = None
    max_results: int = Field(default=5, ge=1, le=50)


class ResearchAssignment(StrictModel):
    assignment_id: str = Field(default_factory=lambda: f"asg-{uuid4().hex[:10]}")
    branch: BranchName
    manager: ManagerName
    objective: str
    required_questions: list[str] = Field(default_factory=list)
    search_queries: list[SearchQuery] = Field(default_factory=list)
    source_tier_targets: list[SourceTier] = Field(default_factory=list)
    max_sources: int = Field(default=8, ge=1, le=100)
    dependencies: list[BranchName] = Field(default_factory=list)


class ResearchPlan(StrictModel):
    plan_id: str = Field(default_factory=lambda: f"plan-{uuid4().hex[:10]}")
    brief: ResearchBrief
    selected_branches: list[BranchName]
    assignments: list[ResearchAssignment]
    branch_rationale: dict[BranchName, str] = Field(default_factory=dict)
    clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def assignments_match_selection(self) -> ResearchPlan:
        assignment_branches = {item.branch for item in self.assignments}
        missing = set(self.selected_branches) - assignment_branches
        if missing:
            raise ValueError(
                f"selected branches missing assignments: {sorted(m.value for m in missing)}"
            )
        return self


class CountryComparison(StrictModel):
    country: str
    comparator_reason: str
    government_level: str
    policy_design: str
    eligibility: str
    funding: str
    risk_allocation: str
    administration: str
    outcomes: str
    institutional_differences: list[str]
    transferability: str
    evidence_quality: EvidenceStrength
    source_ids: list[str] = Field(default_factory=list)


class SourceRecord(StrictModel):
    source_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{1,80}$")
    title: str
    url: str | None = None
    publisher: str | None = None
    author: str | None = None
    publication_date: date | None = None
    access_date: date = Field(default_factory=date.today)
    source_type: SourceType
    tier: SourceTier
    jurisdiction: str | None = None
    excerpt: str = ""
    metadata_status: str = "complete"
    synthetic: bool = False
    retrieved_by: list[str] = Field(default_factory=list)
    used_by: list[str] = Field(default_factory=list)
    supports_claim_ids: list[str] = Field(default_factory=list)
    contradicts_claim_ids: list[str] = Field(default_factory=list)
    safety_flags: list[str] = Field(default_factory=list)
    content_hash: str | None = None

    @model_validator(mode="after")
    def synthetic_metadata(self) -> SourceRecord:
        if self.synthetic and self.source_type != SourceType.SYNTHETIC_FIXTURE:
            raise ValueError("synthetic sources must use source_type=synthetic_fixture")
        return self


class EvidenceClaim(StrictModel):
    claim_id: str = Field(default_factory=lambda: f"claim-{uuid4().hex[:10]}")
    text: str
    claim_type: ClaimType
    supporting_source_ids: list[str] = Field(default_factory=list)
    contradicting_source_ids: list[str] = Field(default_factory=list)
    evidence_strength: EvidenceStrength
    confidence: float = Field(ge=0, le=1)
    geographic_scope: str | None = None
    applicable_period: str | None = None
    material_limitations: list[str] = Field(default_factory=list)
    originating_agent: str


class Contradiction(StrictModel):
    contradiction_id: str = Field(default_factory=lambda: f"contra-{uuid4().hex[:10]}")
    claim_id: str
    supporting_source_ids: list[str] = Field(default_factory=list)
    contradicting_source_ids: list[str] = Field(default_factory=list)
    description: str
    resolution_status: str = "unresolved"
    manager_commentary: str | None = None


class SpecialistFinding(StrictModel):
    branch: BranchName
    agent_name: str
    status: BranchStatus
    summary: str
    claims: list[EvidenceClaim] = Field(default_factory=list)
    discovered_sources: list[SourceRecord] = Field(default_factory=list)
    country_comparisons: list[CountryComparison] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    missing_perspectives: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    prompt_injection_flags: list[str] = Field(default_factory=list)
    error: str | None = None
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime = Field(default_factory=utc_now)


class ManagerSynthesis(StrictModel):
    manager: ManagerName
    status: BranchStatus
    specialist_branches: list[BranchName]
    branch_statuses: dict[BranchName, BranchStatus]
    findings: list[SpecialistFinding] = Field(default_factory=list)
    country_comparisons: list[CountryComparison] = Field(default_factory=list)
    reconciled_claims: list[EvidenceClaim] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    agreements: list[str] = Field(default_factory=list)
    disagreements: list[str] = Field(default_factory=list)
    incentive_driven_claims: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class PolicyOption(StrictModel):
    option_id: str
    name: str
    description: str
    mechanism: str
    expected_benefits: list[str] = Field(default_factory=list)
    expected_costs: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    mitigants: list[str] = Field(default_factory=list)
    implementation_requirements: list[str] = Field(default_factory=list)
    evidence_strength: EvidenceStrength
    source_ids: list[str] = Field(default_factory=list)


class DecisionCriterion(StrictModel):
    criterion_id: str
    name: str
    description: str
    scale: str = "1=low / 5=high"


class DecisionScoreDetail(StrictModel):
    range: str
    note: str = ""

    @field_validator("range")
    @classmethod
    def validate_range(cls, value: str) -> str:
        normalized = value.strip().replace("–", "-").replace("—", "-").replace(" ", "")
        parts = normalized.split("-")
        if len(parts) not in {1, 2} or any(not part.isdigit() for part in parts):
            raise ValueError("score range must be a point or range from 1 to 5")
        bounds = [int(part) for part in parts]
        if any(bound < 1 or bound > 5 for bound in bounds) or bounds != sorted(bounds):
            raise ValueError("score range must be ordered and within 1 to 5")
        return "-".join(str(bound) for bound in bounds)


DecisionScore = int | Literal["low", "medium", "high"] | DecisionScoreDetail


class DecisionMatrix(StrictModel):
    criteria: list[DecisionCriterion]
    options: list[PolicyOption]
    scores: dict[str, dict[str, DecisionScore]]
    caveats: list[str] = Field(default_factory=list)

    @field_validator("scores", mode="before")
    @classmethod
    def normalize_score_labels(cls, value: Any) -> Any:
        """Normalize common qualitative model output to the canonical 1-5 scale."""
        if not isinstance(value, dict):
            return value
        labels = {"low": 1, "medium": 3, "high": 5}
        normalized: dict[Any, Any] = {}
        for option_id, criteria in value.items():
            if not isinstance(criteria, dict):
                normalized[option_id] = criteria
                continue
            normalized[option_id] = {}
            for criterion_id, score in criteria.items():
                if isinstance(score, str):
                    lowered = score.strip().lower()
                    if lowered in labels:
                        score = labels[lowered]
                    elif lowered.isdigit() and 1 <= int(lowered) <= 5:
                        score = int(lowered)
                normalized[option_id][criterion_id] = score
        return normalized

    @model_validator(mode="after")
    def every_option_has_scores(self) -> DecisionMatrix:
        option_ids = {item.option_id for item in self.options}
        if set(self.scores) != option_ids:
            raise ValueError("decision matrix scores must include every policy option exactly once")
        criterion_ids = {item.criterion_id for item in self.criteria}
        for option_id, values in self.scores.items():
            missing = criterion_ids - set(values)
            if missing:
                raise ValueError(f"option {option_id} is missing criteria: {sorted(missing)}")
            invalid = {
                criterion_id: score
                for criterion_id, score in values.items()
                if not (
                    (isinstance(score, int) and 1 <= score <= 5)
                    or isinstance(score, DecisionScoreDetail)
                )
            }
            if invalid:
                raise ValueError(f"option {option_id} has scores outside 1-5: {invalid}")
        return self


class ReportParagraph(StrictModel):
    paragraph_id: str = Field(default_factory=lambda: f"para-{uuid4().hex[:10]}")
    text: str
    citation_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    substantive: bool = True
    revision_note: str | None = None


class ReportSection(StrictModel):
    section_id: str
    title: str
    paragraphs: list[ReportParagraph] = Field(default_factory=list)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Small convenience for the report builder's compact section literals.
        if args:
            if len(args) != 3 or kwargs:
                raise TypeError(
                    "ReportSection positional form requires section_id, title, paragraphs"
                )
            kwargs = {"section_id": args[0], "title": args[1], "paragraphs": args[2]}
        super().__init__(**kwargs)


class DraftReport(StrictModel):
    report_id: str = Field(default_factory=lambda: f"report-{uuid4().hex[:10]}")
    title: str
    executive_summary: str
    sections: list[ReportSection]
    decision_matrix: DecisionMatrix
    source_ids_used: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    disclosures: list[str] = Field(
        default_factory=lambda: [
            "This report is research assistance, not legal advice.",
            "Sources must be verified before formal reliance.",
            "Forecasts and policy conclusions are uncertain.",
        ]
    )
    revised: bool = False
    revision_count: int = 0


class ReviewFinding(StrictModel):
    finding_id: str = Field(default_factory=lambda: f"finding-{uuid4().hex[:10]}")
    severity: str
    affected_section: str
    disputed_claim: str
    explanation: str
    evidence_involved: list[str] = Field(default_factory=list)
    recommended_correction: str
    mandatory_revision: bool = False


class AdversarialReview(StrictModel):
    review_id: str = Field(default_factory=lambda: f"review-{uuid4().hex[:10]}")
    findings: list[ReviewFinding] = Field(default_factory=list)
    citation_completeness: float = Field(ge=0, le=1)
    grounding_score: float = Field(ge=0, le=5)
    balance_score: float = Field(ge=0, le=5)
    calibration_score: float = Field(ge=0, le=5)
    security_score: float = Field(ge=0, le=5)
    release_recommendation: ReleaseRecommendation
    reviewer_notes: list[str] = Field(default_factory=list)


class RunMetrics(StrictModel):
    run_id: str
    started_at: datetime
    finished_at: datetime | None = None
    latency_ms: int | None = None
    total_tokens: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    approximate_cost_usd: float | None = None
    model: str | None = None
    trace_id: str | None = None
    branch_statuses: dict[str, BranchStatus] = Field(default_factory=dict)
    retries: dict[str, int] = Field(default_factory=dict)
    validation_failures: list[str] = Field(default_factory=list)
    evaluation_scores: dict[str, float] = Field(default_factory=dict)


class FinalResearchPackage(StrictModel):
    run_id: str
    request: UserResearchRequest
    brief: ResearchBrief
    plan: ResearchPlan
    specialist_findings: list[SpecialistFinding]
    manager_syntheses: list[ManagerSynthesis]
    source_ledger: list[SourceRecord]
    draft_report: DraftReport
    adversarial_review: AdversarialReview
    final_report: DraftReport
    metrics: RunMetrics
    created_at: datetime = Field(default_factory=utc_now)
