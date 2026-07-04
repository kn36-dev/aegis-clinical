from datetime import datetime, timezone
from uuid import uuid4

from aegis.models.patient import BiologicalSex, Demographics, Patient
from aegis.models.workflow import WorkflowState


def test_workflow_initial_state():
    state = WorkflowState()

    assert state.patient is None
    assert state.clinical_note is None
    assert state.taxonomy_candidates == ()
    assert state.icd_suggestions == ()
    assert state.physician_review is None
    assert state.trial_matches == ()


def test_workflow_is_mutable():
    state = WorkflowState()

    state.current_step = "vector_retrieval"

    assert state.current_step == "vector_retrieval"


def test_workflow_round_trip():
    state = WorkflowState(
        current_step="icd_reasoning",
        trace_id=uuid4(),
    )

    restored = WorkflowState.model_validate(state.model_dump())

    assert restored == state


def test_workflow_json_round_trip():
    state = WorkflowState(
        current_step="physician_review",
        trace_id=uuid4(),
    )

    restored = WorkflowState.model_validate_json(state.model_dump_json())

    assert restored == state


def test_workflow_supports_partial_execution():
    state = WorkflowState(
        current_step="vector_retrieval",
    )

    assert state.patient is None
    assert state.clinical_note is None
    assert state.taxonomy_candidates == ()
    assert state.icd_suggestions == ()


def test_workflow_allows_incremental_building():
    state = WorkflowState()

    patient = Patient(
        patient_id=uuid4(),
        medical_record_number="MRN-001",
        date_of_birth=datetime.now(timezone.utc).date(),
        demographics=Demographics(
            biological_sex=BiologicalSex.MALE,
        ),
    )

    state.patient = patient

    assert state.patient == patient


def test_workflow_state_round_trip():
    state = WorkflowState(
        current_step="symptom_extraction",
        trace_id=uuid4(),
    )

    restored = WorkflowState.model_validate(state.model_dump())

    assert restored.current_step == "symptom_extraction"
    assert restored.trace_id == state.trace_id


def test_workflow_state_is_mutable():
    state = WorkflowState()

    state.current_step = "symptom_extraction"

    assert state.current_step == "symptom_extraction"
