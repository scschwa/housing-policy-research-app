from datetime import date

import pytest
from pydantic import ValidationError

from housing_policy_agents.models import (
    BranchName,
    BranchStatus,
    DecisionCriterion,
    DecisionMatrix,
    DecisionScoreDetail,
    EvidenceStrength,
    ManagerName,
    ManagerSynthesis,
    PolicyOption,
    SourceRecord,
    SourceTier,
    SourceType,
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


def test_manager_synthesis_accepts_source_ids() -> None:
    synthesis = ManagerSynthesis(
        manager=ManagerName.POLICY,
        status=BranchStatus.COMPLETED,
        specialist_branches=[BranchName.GOVERNMENT],
        branch_statuses={BranchName.GOVERNMENT: BranchStatus.COMPLETED},
        source_ids=["src-example"],
    )

    assert synthesis.source_ids == ["src-example"]
