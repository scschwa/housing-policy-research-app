from datetime import date

import pytest
from pydantic import ValidationError

from housing_policy_agents.models import (
    DecisionCriterion,
    DecisionMatrix,
    EvidenceStrength,
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
