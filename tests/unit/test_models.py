from datetime import date

import pytest
from pydantic import ValidationError

from housing_policy_agents.models import (
    BranchName,
    BranchStatus,
    DecisionCriterion,
    DecisionMatrix,
    DecisionScoreDetail,
    EvidenceClaim,
    EvidenceStrength,
    ManagerName,
    ManagerSynthesis,
    PolicyOption,
    SourceRecord,
    SourceTier,
    SourceType,
    SpecialistFinding,
    canonical_source_id,
)


def option(option_id: str) -> PolicyOption:
    return PolicyOption(
        option_id=option_id,
        name=option_id,
        description="demo",
        mechanism="demo",
        evidence_strength=EvidenceStrength.MODERATE,
    )


def test_source_record_rejects_inconsistent_synthetic_type() -> None:
    with pytest.raises(ValidationError):
        SourceRecord(
            source_id="S-1",
            title="bad",
            source_type=SourceType.COMMENTARY,
            tier=SourceTier.COMMENTARY_OR_UNVERIFIED,
            synthetic=True,
            access_date=date.today(),
        )


def test_specialist_finding_normalizes_url_source_ids() -> None:
    url = "https://www.fhfa.gov/document/chattel-pilot.pdf?utm_source=openai"
    source_id = canonical_source_id(url)
    finding = SpecialistFinding.model_validate(
        {
            "branch": BranchName.GOVERNMENT,
            "agent_name": "government_sources_researcher",
            "status": BranchStatus.COMPLETED,
            "summary": "The source establishes a current policy constraint.",
            "claims": [
                EvidenceClaim(
                    claim_id="c1",
                    text="The source identifies a policy constraint.",
                    claim_type="fact",
                    why_it_matters="It affects implementation feasibility.",
                    manager_implication="Carry the constraint into the options analysis.",
                    supporting_source_ids=[url],
                    evidence_strength="strong",
                    confidence=0.9,
                    originating_agent="government_sources_researcher",
                ).model_dump(mode="json")
            ],
            "discovered_sources": [
                {
                    "source_id": url,
                    "title": "Chattel pilot materials",
                    "source_type": SourceType.AGENCY_GUIDANCE,
                    "tier": SourceTier.AUTHORITATIVE_PRIMARY,
                    "excerpt": "The relevant policy text.",
                }
            ],
            "source_ids": [url],
        }
    )

    assert finding.discovered_sources[0].source_id == source_id
    assert finding.discovered_sources[0].url == url
    assert finding.claims[0].supporting_source_ids == [source_id]
    assert finding.source_ids == [source_id]


def test_decision_matrix_requires_every_option_and_criterion() -> None:
    criterion = DecisionCriterion(criterion_id="benefit", name="Benefit", description="Benefit")
    with pytest.raises(ValidationError):
        DecisionMatrix(
            criteria=[criterion],
            options=[option("O1"), option("O2")],
            scores={"O1": {"benefit": 4}},
        )


def test_decision_matrix_normalizes_qualitative_scores() -> None:
    criterion = DecisionCriterion(criterion_id="benefit", name="Benefit", description="Benefit")
    matrix = DecisionMatrix(
        criteria=[criterion],
        options=[option("O1")],
        scores={"O1": {"benefit": "high"}},
    )

    assert matrix.scores == {"O1": {"benefit": 5}}


def test_decision_matrix_accepts_qualitative_score_ranges() -> None:
    criterion = DecisionCriterion(criterion_id="benefit", name="Benefit", description="Benefit")
    matrix = DecisionMatrix(
        criteria=[criterion],
        options=[option("O1")],
        scores={"O1": {"benefit": {"range": "1-3", "note": "conditional"}}},
    )

    score = matrix.scores["O1"]["benefit"]
    assert isinstance(score, DecisionScoreDetail)
    assert score.range == "1-3"


def test_decision_matrix_normalizes_transposed_scores() -> None:
    criteria = [
        DecisionCriterion(criterion_id="benefit", name="Benefit", description="Benefit"),
        DecisionCriterion(criterion_id="risk", name="Risk", description="Risk"),
    ]
    matrix = DecisionMatrix(
        criteria=criteria,
        options=[option("O1"), option("O2")],
        scores={
            "benefit": {"O1": "high", "O2": "medium"},
            "risk": {"O1": "low", "O2": "high"},
        },
    )

    assert matrix.scores == {
        "O1": {"benefit": 5, "risk": 1},
        "O2": {"benefit": 3, "risk": 5},
    }


def test_manager_synthesis_accepts_source_ids() -> None:
    synthesis = ManagerSynthesis(
        manager=ManagerName.POLICY,
        status=BranchStatus.COMPLETED,
        specialist_branches=[BranchName.GOVERNMENT],
        branch_statuses={BranchName.GOVERNMENT: BranchStatus.COMPLETED},
        source_ids=["src-example"],
    )

    assert synthesis.source_ids == ["src-example"]
