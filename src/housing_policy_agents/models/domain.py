"""Pydantic models used at all major workflow boundaries."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from datetime import UTC, date, datetime
from enum import IntEnum, StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


def _coerce_date(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return value
    return value


def _coerce_datetime(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    return value


def _normalize_evidence_strength(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    for strength in EvidenceStrength:
        if normalized == strength.value or normalized.startswith(f"{strength.value}_"):
            return strength.value
    if normalized.startswith(("limited", "insufficient", "minimal")):
        return EvidenceStrength.WEAK.value
    return value


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


class RepairStatus(StrEnum):
    REPAIRED = "repaired"
    WITHHELD = "withheld"
    UNCHANGED = "unchanged"


class RunMode(StrEnum):
    INTERACTIVE = "interactive"
    FAST = "fast"


class ResearchProviderName(StrEnum):
    OFFLINE = "offline"
    WEB = "web"


MAX_RESEARCH_QUESTION_CHARS = 4_000
MAX_SEARCH_QUERY_CHARS = 500


class UserResearchRequest(StrictModel):
    request_id: str = Field(default_factory=lambda: f"req-{uuid4().hex[:12]}")
    question: str = Field(min_length=20, max_length=MAX_RESEARCH_QUESTION_CHARS)
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
    text: str = Field(min_length=5, max_length=MAX_SEARCH_QUERY_CHARS)
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
    research_context: str = ""
    in_scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    preferred_sources: list[str] = Field(default_factory=list)
    policy_decisions_supported: list[str] = Field(default_factory=list)
    handoff_instructions: list[str] = Field(default_factory=list)
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

    @field_validator("evidence_quality", mode="before")
    @classmethod
    def normalize_quality(cls, value: Any) -> Any:
        return _normalize_evidence_strength(value)


_SOURCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,80}$")


def canonical_source_id(value: str) -> str:
    """Return a stable internal ID while leaving already-valid IDs unchanged."""

    text = value.strip()
    if _SOURCE_ID_PATTERN.fullmatch(text):
        return text
    if text.lower().startswith(("http://", "https://")):
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
        return f"s_{digest}"
    return text


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

    @model_validator(mode="before")
    @classmethod
    def normalize_url_source_id(cls, value: Any) -> Any:
        """Keep model-generated URLs usable without weakening the internal ID contract."""

        if not isinstance(value, Mapping):
            return value
        updated = dict(value)
        for field in ("publication_date", "access_date"):
            if field in updated:
                updated[field] = _coerce_date(updated[field])
        raw_id = value.get("source_id")
        if not isinstance(raw_id, str) or not raw_id.strip().lower().startswith(
            ("http://", "https://")
        ):
            return updated
        updated["source_id"] = canonical_source_id(raw_id)
        updated["url"] = updated.get("url") or raw_id
        return updated

    @model_validator(mode="after")
    def synthetic_metadata(self) -> SourceRecord:
        if self.synthetic and self.source_type != SourceType.SYNTHETIC_FIXTURE:
            raise ValueError("synthetic sources must use source_type=synthetic_fixture")
        return self


class EvidenceClaim(StrictModel):
    claim_id: str = Field(default_factory=lambda: f"claim-{uuid4().hex[:10]}")
    text: str
    claim_type: ClaimType
    why_it_matters: str = ""
    manager_implication: str = ""
    supporting_source_ids: list[str] = Field(default_factory=list)
    contradicting_source_ids: list[str] = Field(default_factory=list)
    evidence_strength: EvidenceStrength
    confidence: float = Field(ge=0, le=1)
    geographic_scope: str | None = None
    applicable_period: str | None = None
    material_limitations: list[str] = Field(default_factory=list)
    originating_agent: str

    @field_validator("evidence_strength", mode="before")
    @classmethod
    def normalize_strength(cls, value: Any) -> Any:
        return _normalize_evidence_strength(value)


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

    @model_validator(mode="before")
    @classmethod
    def normalize_source_references(cls, value: Any) -> Any:
        """Normalize URL-shaped IDs before strict nested validation.

        Live research models occasionally place a retrieved URL in ``source_id``
        even though the application uses short IDs internally. The URL remains
        available in ``SourceRecord.url`` while every claim/reference points to
        the same deterministic internal ID.
        """

        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        for field in ("started_at", "finished_at"):
            if field in payload:
                payload[field] = _coerce_datetime(payload[field])
        aliases: dict[str, str] = {}
        raw_sources = payload.get("discovered_sources") or []
        normalized_sources: list[Any] = []
        for raw_source in raw_sources:
            if isinstance(raw_source, Mapping):
                source = dict(raw_source)
                raw_id = source.get("source_id")
                if isinstance(raw_id, str):
                    normalized = canonical_source_id(raw_id)
                    if normalized != raw_id:
                        aliases[raw_id] = normalized
                        source["source_id"] = normalized
                        if source.get("url") is None:
                            source["url"] = raw_id
                normalized_sources.append(source)
            else:
                normalized_sources.append(raw_source)
        if raw_sources:
            payload["discovered_sources"] = normalized_sources

        def remap_ids(values: Any) -> Any:
            if not isinstance(values, list):
                return values
            return [
                aliases.get(item, canonical_source_id(item) if isinstance(item, str) else item)
                for item in values
            ]

        for field in ("source_ids",):
            if field in payload:
                payload[field] = remap_ids(payload[field])
        for field in ("claims", "contradictions"):
            items = payload.get(field) or []
            normalized_items: list[Any] = []
            for raw_item in items:
                if not isinstance(raw_item, Mapping):
                    normalized_items.append(raw_item)
                    continue
                item = dict(raw_item)
                for reference_field in ("supporting_source_ids", "contradicting_source_ids"):
                    if reference_field in item:
                        item[reference_field] = remap_ids(item[reference_field])
                normalized_items.append(item)
            if field in payload:
                payload[field] = normalized_items
        comparisons = payload.get("country_comparisons") or []
        normalized_comparisons: list[Any] = []
        for raw_comparison in comparisons:
            if not isinstance(raw_comparison, Mapping):
                normalized_comparisons.append(raw_comparison)
                continue
            comparison = dict(raw_comparison)
            if "source_ids" in comparison:
                comparison["source_ids"] = remap_ids(comparison["source_ids"])
            normalized_comparisons.append(comparison)
        if "country_comparisons" in payload:
            payload["country_comparisons"] = normalized_comparisons
        return payload


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

    @field_validator("evidence_strength", mode="before")
    @classmethod
    def normalize_strength(cls, value: Any) -> Any:
        return _normalize_evidence_strength(value)


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

    @model_validator(mode="before")
    @classmethod
    def move_embedded_caveats(cls, value: Any) -> Any:
        """Accept a common model shape that nests matrix caveats under scores."""
        if not isinstance(value, Mapping):
            return value
        updated = dict(value)
        raw_scores = updated.get("scores")
        if not isinstance(raw_scores, Mapping) or "caveats" not in raw_scores:
            return updated
        embedded = raw_scores.get("caveats")
        updated["scores"] = {
            key: item for key, item in raw_scores.items() if key != "caveats"
        }
        if isinstance(embedded, list):
            existing = updated.get("caveats") or []
            updated["caveats"] = [*existing, *embedded]
        return updated

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
        criterion_ids = {item.criterion_id for item in self.criteria}
        if set(self.scores) == criterion_ids:
            nested_ids = {key for values in self.scores.values() for key in values}
            if nested_ids == option_ids:
                self.scores = {
                    option_id: {
                        criterion_id: self.scores[criterion_id][option_id]
                        for criterion_id in criterion_ids
                    }
                    for option_id in option_ids
                }
        if set(self.scores) != option_ids:
            raise ValueError("decision matrix scores must include every policy option exactly once")
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
    withheld: bool = False
    withheld_reason: str | None = None


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
    executive_summary_withheld: bool = False
    decision_matrix_withheld: bool = False
    withheld_components: list[str] = Field(default_factory=list)


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


class ReportAuditEntry(StrictModel):
    audit_id: str = Field(default_factory=lambda: f"audit-{uuid4().hex[:10]}")
    stage: str
    issue_code: str
    issue: str
    target_type: str
    target_id: str
    section_id: str | None = None
    original_content: str
    withheld_content: str
    revised_content: str | None = None
    status: RepairStatus
    attempts: int = 0
    citation_ids_before: list[str] = Field(default_factory=list)
    citation_ids_after: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ReportAudit(StrictModel):
    run_id: str
    entries: list[ReportAuditEntry] = Field(default_factory=list)
    repair_passes: int = 0
    initial_error_count: int = 0
    final_error_count: int = 0


class AgentUsageRecord(StrictModel):
    interaction_id: str
    agent: str
    stage: str
    model: str | None = None
    status: str
    requests: int = 0
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    duration_ms: int = 0
    approximate_cost_usd: float | None = None
    pricing_model: str | None = None
    pricing_source_url: str | None = None
    pricing_verified_on: str | None = None
    input_rate_per_million_usd: float | None = None
    cached_input_rate_per_million_usd: float | None = None
    cache_write_rate_per_million_usd: float | None = None
    output_rate_per_million_usd: float | None = None
    long_context_pricing_applied: bool = False
    cost_is_estimate: bool = True


class UsageReport(StrictModel):
    run_id: str
    model: str | None = None
    records: list[AgentUsageRecord] = Field(default_factory=list)
    requests: int = 0
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    wall_clock_ms: int = 0
    cumulative_agent_ms: int = 0
    approximate_cost_usd: float | None = None
    pricing_note: str
    pricing_catalog_version: str | None = None
    pricing_source_url: str | None = None
    cost_is_estimate: bool = True
    concurrency_note: str = (
        "Agent durations are cumulative and may exceed wall-clock time because branches run concurrently."
    )


class RunMetrics(StrictModel):
    run_id: str
    started_at: datetime
    finished_at: datetime | None = None
    latency_ms: int | None = None
    total_tokens: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    approximate_cost_usd: float | None = None
    requests: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    reasoning_tokens: int = 0
    cumulative_agent_ms: int = 0
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
    audit_report: ReportAudit | None = None
    usage_report: UsageReport | None = None
    created_at: datetime = Field(default_factory=utc_now)
