from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegis.models.trial import (
    CriterionType,
    MatchStatus,
    Trial,
    TrialCriterion,
    TrialMatch,
)


def test_criterion_construction():
    criterion = TrialCriterion(
        criterion_type=CriterionType.INCLUSION,
        description="Age ≥ 18",
    )

    assert criterion.criterion_type is CriterionType.INCLUSION


def test_criterion_requires_description():
    with pytest.raises(ValidationError):
        TrialCriterion.model_validate(
            {
                "criterion_type": CriterionType.INCLUSION,
            }
        )


def test_criterion_round_trip():
    criterion = TrialCriterion(
        criterion_type=CriterionType.EXCLUSION,
        description="Pregnancy",
    )

    restored = TrialCriterion.model_validate(criterion.model_dump())

    assert restored == criterion


def test_trial_construction():
    trial = Trial(
        trial_id=uuid4(),
        title="NSCLC Immunotherapy Trial",
        criteria=(
            TrialCriterion(
                criterion_type=CriterionType.INCLUSION,
                description="Age ≥ 18",
            ),
        ),
    )

    assert len(trial.criteria) == 1


def test_trial_round_trip():
    trial = Trial(
        trial_id=uuid4(),
        title="NSCLC Immunotherapy Trial",
        criteria=(),
    )

    restored = Trial.model_validate(trial.model_dump())

    assert restored == trial


def test_match_construction():
    match = TrialMatch(
        patient_id=uuid4(),
        trial_id=uuid4(),
        status=MatchStatus.MATCHED,
        reasons=("Eligible.",),
    )

    assert match.status is MatchStatus.MATCHED


def test_match_requires_status():
    with pytest.raises(ValidationError):
        TrialMatch.model_validate(
            {
                "patient_id": uuid4(),
                "trial_id": uuid4(),
                "reasons": [],
            }
        )


def test_match_round_trip():
    match = TrialMatch(
        patient_id=uuid4(),
        trial_id=uuid4(),
        status=MatchStatus.PARTIAL,
        reasons=("One inclusion criterion pending.",),
    )

    restored = TrialMatch.model_validate(match.model_dump())

    assert restored == match
