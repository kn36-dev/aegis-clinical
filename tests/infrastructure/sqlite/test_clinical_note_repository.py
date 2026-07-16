from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from aegis.infrastructure.sqlite.clinical_note_repository import SQLiteClinicalNoteRepository
from aegis.models.clinical_note import ClinicalNote


def _seed_patient_identity(conn: sqlite3.Connection, patient_id: UUID) -> None:
    conn.execute(
        """
        INSERT INTO patient_identity_vault (
            patient_id, medical_record_number, first_name, last_name, date_of_birth
        ) VALUES (?, ?, ?, ?, ?);
        """,
        (str(patient_id), f"MRN-{patient_id}", "Jane", "Doe", "1990-01-01"),
    )
    conn.commit()


def _build_clinical_note(patient_id: UUID, case_id: UUID | None = None) -> ClinicalNote:
    return ClinicalNote(
        case_id=case_id or uuid4(),
        patient_id=patient_id,
        content_reference="content-store://clinical-notes/abc123",
        created_at=datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc),
    )


def test_round_trip_persistence(clinical_db_connection: sqlite3.Connection) -> None:
    patient_id = uuid4()
    _seed_patient_identity(clinical_db_connection, patient_id)
    clinical_note = _build_clinical_note(patient_id)

    repository = SQLiteClinicalNoteRepository(clinical_db_connection)
    repository.save(clinical_note)
    retrieved = repository.get_by_case_id(clinical_note.case_id)

    assert retrieved == clinical_note


def test_round_trip_preserves_all_fields_without_loss(
    clinical_db_connection: sqlite3.Connection,
) -> None:
    patient_id = uuid4()
    _seed_patient_identity(clinical_db_connection, patient_id)
    clinical_note = _build_clinical_note(patient_id)

    repository = SQLiteClinicalNoteRepository(clinical_db_connection)
    repository.save(clinical_note)
    retrieved = repository.get_by_case_id(clinical_note.case_id)

    assert retrieved is not None
    assert retrieved.case_id == clinical_note.case_id
    assert retrieved.patient_id == clinical_note.patient_id
    assert retrieved.content_reference == clinical_note.content_reference
    assert retrieved.created_at == clinical_note.created_at


def test_get_by_case_id_returns_none_when_absent(
    clinical_db_connection: sqlite3.Connection,
) -> None:
    repository = SQLiteClinicalNoteRepository(clinical_db_connection)

    assert repository.get_by_case_id(uuid4()) is None


def test_save_rejects_unknown_patient_with_clear_failure(
    clinical_db_connection: sqlite3.Connection,
) -> None:
    """Foreign-key violations must propagate rather than silently corrupting state."""
    clinical_note = _build_clinical_note(patient_id=uuid4())
    repository = SQLiteClinicalNoteRepository(clinical_db_connection)

    with pytest.raises(sqlite3.IntegrityError):
        repository.save(clinical_note)

    assert repository.get_by_case_id(clinical_note.case_id) is None


def test_save_rejects_duplicate_case_id(clinical_db_connection: sqlite3.Connection) -> None:
    patient_id = uuid4()
    _seed_patient_identity(clinical_db_connection, patient_id)
    clinical_note = _build_clinical_note(patient_id)
    repository = SQLiteClinicalNoteRepository(clinical_db_connection)
    repository.save(clinical_note)

    with pytest.raises(sqlite3.IntegrityError):
        repository.save(clinical_note)


def test_round_trip_result_is_a_domain_model_not_a_raw_row(
    clinical_db_connection: sqlite3.Connection,
) -> None:
    """Boundary protection: no sqlite Row/connection/dict should leak past the repository."""
    patient_id = uuid4()
    _seed_patient_identity(clinical_db_connection, patient_id)
    clinical_note = _build_clinical_note(patient_id)
    repository = SQLiteClinicalNoteRepository(clinical_db_connection)
    repository.save(clinical_note)

    retrieved = repository.get_by_case_id(clinical_note.case_id)

    assert isinstance(retrieved, ClinicalNote)
    assert not isinstance(retrieved, sqlite3.Row)
    assert not isinstance(retrieved, dict)
