# WorkflowState

# Owns

# everything the LangGraph nodes need.

# It is not your database schema.

# It is not your API request.

# It is the graph state.

# WorkflowState

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict

from aegis.models.base import DomainModel
from aegis.models.clinical_note import ClinicalNote
from aegis.models.icd import ICDSuggestion
from aegis.models.patient import Patient
from aegis.models.review import PhysicianReview
from aegis.models.symptom import SymptomExtraction
from aegis.models.trial import TrialMatch


class WorkflowState(DomainModel):
    """
    Mutable LangGraph execution state.

    This is NOT a domain model.

    It is the orchestration container that flows through the graph.
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
        str_strip_whitespace=True,
    )

    # Identity context
    patient: Patient | None = None
    clinical_note: ClinicalNote | None = None

    # AI pipeline outputs
    symptom_extraction: SymptomExtraction | None = None
    icd_suggestions: tuple[ICDSuggestion, ...] = ()

    # Human-in-the-loop
    physician_review: PhysicianReview | None = None

    # Downstream analytics
    trial_matches: tuple[TrialMatch, ...] = ()

    # Execution metadata
    current_step: str | None = None
    last_updated: datetime | None = None
    trace_id: UUID | None = None
