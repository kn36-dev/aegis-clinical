from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegis.models.clinical_note import ClinicalNote


@pytest.fixture
def clinical_note():
    return ClinicalNote(
        note_id=uuid4(),
        patient_id=uuid4(),
        physician_id=uuid4(),
        raw_text="""
        Patient reports persistent productive cough for five days.
        No fever.
        Mild shortness of breath.
        """,
        created_at=datetime.now(timezone.utc),
    )


def test_clinical_note_construction(clinical_note):
    assert clinical_note.raw_text.startswith("Patient")
    assert clinical_note.note_id is not None


def test_clinical_note_requires_raw_text():
    with pytest.raises(ValidationError):
        ClinicalNote.model_validate(
            {
                "note_id": uuid4(),
                "patient_id": uuid4(),
                "physician_id": uuid4(),
                "created_at": datetime.now(timezone.utc),
            }
        )


def test_clinical_note_rejects_empty_text():
    with pytest.raises(ValidationError):
        ClinicalNote(
            note_id=uuid4(),
            patient_id=uuid4(),
            physician_id=uuid4(),
            raw_text="",
            created_at=datetime.now(timezone.utc),
        )


def test_clinical_note_is_immutable(clinical_note):
    with pytest.raises(ValidationError):
        clinical_note.raw_text = "Modified"


def test_clinical_note_serialization_round_trip(clinical_note):
    dumped = clinical_note.model_dump()

    restored = ClinicalNote.model_validate(dumped)

    assert restored == clinical_note


def test_clinical_note_json_round_trip(clinical_note):
    json_data = clinical_note.model_dump_json()

    restored = ClinicalNote.model_validate_json(json_data)

    assert restored == clinical_note
