"""
SQLiteClinicalNoteRepository

Concrete SQLite adapter for the ``ClinicalNoteRepository`` protocol
(``aegis.services.clinical_note_service``).

Maps the immutable ``ClinicalNote`` domain artifact onto the ``patient_case``
table (see migrations 0002 and 0010). Owns SQL execution, serialization, and
persistence mapping only -- it performs no validation of clinical content,
identifier generation, or workflow decisions; those belong to
``ClinicalNoteService``.

Two columns on ``patient_case`` are workflow/orchestration concerns that
``ClinicalNote`` itself does not carry: ``thread_id`` and ``status``.
``thread_id`` is derived deterministically from ``case_id`` (V1: a workflow
checkpoint identity, not a domain identity -- ``str(case_id)``); ``status``
is initialized to ``"pending_ai"``, the entry point of the documented
status lifecycle (``PENDING_AI`` -> ``PENDING_HITL`` / ``ARCHIVED``). Neither
value is read back into the reconstructed ``ClinicalNote`` -- they never
cross the repository boundary outward.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from uuid import UUID

from aegis.models.clinical_note import ClinicalNote

_INITIAL_CASE_STATUS = "pending_ai"


class SQLiteClinicalNoteRepository:
    """
    ``ClinicalNoteRepository`` implementation backed by the clinical
    registry SQLite database.

    Structurally satisfies ``aegis.services.clinical_note_service.ClinicalNoteRepository``
    (``save``). ``get_by_case_id`` is an additional capability beyond that
    protocol, provided for independent adapter verification (round-trip
    testing) -- callers that only need the protocol boundary should depend
    on ``ClinicalNoteRepository``, not this concrete class.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection

    def save(self, clinical_note: ClinicalNote) -> None:
        """
        Persist ``clinical_note``, idempotently.

        Re-saving the same ``case_id`` with an unchanged ``patient_id`` and
        ``content_reference`` is a no-op rather than a constraint violation.
        This is what makes ``POST /clinical-notes/ingest`` retry-safe: it
        calls ``ClinicalNoteService.create_clinical_note`` directly to
        establish this row (so ``clinical_note_content`` has something to
        foreign-key against) before seeding content, and then the graph's
        own ``create_clinical_note`` node persists the identical artifact
        again moments later. ``created_at`` is deliberately excluded from
        the comparison -- each call to ``create_clinical_note`` stamps its
        own timestamp, so two persist attempts for the same submission
        never share one. A ``case_id`` reused with a *different*
        ``patient_id`` or ``content_reference`` still raises -- that is a
        genuine identity conflict, not a retry.
        """
        existing = self.get_by_case_id(clinical_note.case_id)
        if existing is not None:
            if (
                existing.patient_id == clinical_note.patient_id
                and existing.content_reference == clinical_note.content_reference
            ):
                return
            raise ValueError(
                f"case_id {clinical_note.case_id} is already persisted with a different "
                "patient_id or content_reference"
            )

        cursor = self._conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO patient_case (
                    case_id,
                    patient_id,
                    thread_id,
                    status,
                    ingress_timestamp,
                    content_reference
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    str(clinical_note.case_id),
                    str(clinical_note.patient_id),
                    str(clinical_note.case_id),
                    _INITIAL_CASE_STATUS,
                    clinical_note.created_at.isoformat(),
                    clinical_note.content_reference,
                ),
            )
            self._conn.commit()
        except sqlite3.Error:
            self._conn.rollback()
            raise

    def get_by_case_id(self, case_id: UUID) -> ClinicalNote | None:
        """Adapter-only read path, used by tests to verify round-trip fidelity."""
        row = self._conn.execute(
            """
            SELECT case_id, patient_id, content_reference, ingress_timestamp
            FROM patient_case
            WHERE case_id = ?;
            """,
            (str(case_id),),
        ).fetchone()

        if row is None:
            return None

        content_reference = row["content_reference"]
        if content_reference is None:
            return None

        return ClinicalNote(
            case_id=UUID(row["case_id"]),
            patient_id=UUID(row["patient_id"]),
            content_reference=content_reference,
            created_at=datetime.fromisoformat(row["ingress_timestamp"]),
        )
