# TrialCriterion
# Trial
# TrialMatch

from enum import Enum
from uuid import UUID

from aegis.models.base import DomainModel


class CriterionType(str, Enum):
    INCLUSION = "inclusion"
    EXCLUSION = "exclusion"


class MatchStatus(str, Enum):
    MATCHED = "matched"

    PARTIAL = "partial"

    NOT_MATCHED = "not_matched"


class TrialCriterion(DomainModel):
    """
    One eligibility criterion for a clinical trial.
    """

    criterion_type: CriterionType

    description: str


class Trial(DomainModel):
    """
    Clinical trial metadata.
    """

    trial_id: UUID

    title: str

    summary: str | None = None

    criteria: tuple[TrialCriterion, ...]


class TrialMatch(DomainModel):
    """
    Result of matching one patient against one trial.
    """

    patient_id: UUID

    trial_id: UUID

    status: MatchStatus

    reasons: tuple[str, ...]
