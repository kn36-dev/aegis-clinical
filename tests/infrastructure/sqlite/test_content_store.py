from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from aegis.infrastructure.sqlite.content_store import (
    ContentIntegrityError,
    ContentNotFoundError,
    SQLiteContentStore,
)


def _seed_patient_case(conn: sqlite3.Connection, case_id: UUID) -> None:
    patient_id = uuid4()
    conn.execute(
        """
        INSERT INTO patient_identity_vault (
            patient_id, medical_record_number, first_name, last_name, date_of_birth
        ) VALUES (?, ?, ?, ?, ?);
        """,
        (str(patient_id), f"MRN-{patient_id}", "Jane", "Doe", "1990-01-01"),
    )
    conn.execute(
        """
        INSERT INTO patient_case (
            case_id, patient_id, thread_id, status, ingress_timestamp
        ) VALUES (?, ?, ?, 'pending_ai', ?);
        """,
        (str(case_id), str(patient_id), str(case_id), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def test_round_trip_persistence(clinical_db_connection: sqlite3.Connection) -> None:
    case_id = uuid4()
    _seed_patient_case(clinical_db_connection, case_id)
    content_reference = "content-store://clinical-notes/abc123"
    store = SQLiteContentStore(clinical_db_connection)

    store.save_content(case_id, content_reference, "Patient presents with acute cough.")
    retrieved = store.get_content(content_reference)

    assert retrieved == "Patient presents with acute cough."


def test_get_content_raises_typed_error_when_absent(
    clinical_db_connection: sqlite3.Connection,
) -> None:
    """Boundary protection: a missing reference must raise a repository-level error, not a raw sqlite error or None."""
    store = SQLiteContentStore(clinical_db_connection)

    with pytest.raises(ContentNotFoundError):
        store.get_content("content-store://clinical-notes/missing")


def test_get_content_detects_tampered_payload(clinical_db_connection: sqlite3.Connection) -> None:
    """A corrupted row (checksum no longer matching payload) must fail loudly, not silently."""
    case_id = uuid4()
    _seed_patient_case(clinical_db_connection, case_id)
    content_reference = "content-store://clinical-notes/abc123"
    store = SQLiteContentStore(clinical_db_connection)
    store.save_content(case_id, content_reference, "Original text.")

    clinical_db_connection.execute(
        "UPDATE clinical_note_content SET content_payload = ? WHERE content_reference = ?;",
        ("Tampered text.", content_reference),
    )
    clinical_db_connection.commit()

    with pytest.raises(ContentIntegrityError):
        store.get_content(content_reference)


def test_save_content_rejects_unknown_case(clinical_db_connection: sqlite3.Connection) -> None:
    store = SQLiteContentStore(clinical_db_connection)

    with pytest.raises(sqlite3.IntegrityError):
        store.save_content(uuid4(), "content-store://clinical-notes/orphan", "text")


def test_save_content_rejects_duplicate_reference(
    clinical_db_connection: sqlite3.Connection,
) -> None:
    case_id = uuid4()
    _seed_patient_case(clinical_db_connection, case_id)
    content_reference = "content-store://clinical-notes/abc123"
    store = SQLiteContentStore(clinical_db_connection)
    store.save_content(case_id, content_reference, "text one")

    with pytest.raises(sqlite3.IntegrityError):
        store.save_content(case_id, content_reference, "text two")
