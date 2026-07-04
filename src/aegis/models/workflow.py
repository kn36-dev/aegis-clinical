# WorkflowState

# Owns

# everything the LangGraph nodes need.

# It is not your database schema.

# It is not your API request.

# It is the graph state.

# WorkflowState
from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import ConfigDict

from aegis.models.base import DomainModel
from aegis.models.clinical_note import ClinicalNote
from aegis.models.icd import ICDSuggestion, TaxonomyCandidate
from aegis.models.patient import Patient
from aegis.models.review import PhysicianReview
from aegis.models.trial import TrialMatch


class WorkflowState(DomainModel):
    """
    Mutable execution state shared between LangGraph nodes.

    This model is an orchestration container and is intentionally
    mutable. It should never become a business object.
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
        str_strip_whitespace=True,
    )

    patient: Patient | None = None

    clinical_note: ClinicalNote | None = None

    taxonomy_candidates: tuple[TaxonomyCandidate, ...] = ()

    icd_suggestions: tuple[ICDSuggestion, ...] = ()

    physician_review: PhysicianReview | None = None

    trial_matches: tuple[TrialMatch, ...] = ()

    current_step: str | None = None

    last_updated: datetime | None = None

    trace_id: UUID | None = None


# This workflow step is good for constraining the type of current_step
# so it never falls outside of what the orchestration wants.
class WorkflowStep(str, Enum):
    PHI_REDACTION = "phi_redaction"
    NORMALIZATION = "normalization"
    CACHE_LOOKUP = "cache_lookup"
    VECTOR_RETRIEVAL = "vector_retrieval"
    ICD_REASONING = "icd_reasoning"
    PHYSICIAN_REVIEW = "physician_review"
    TRIAL_MATCHING = "trial_matching"
    PERSISTENCE = "persistence"
