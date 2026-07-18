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

``mark_pending_review``/``mark_archived``/``list_pending_review`` (Slice 4)
maintain and read that same ``status`` column as a queryable projection of
the workflow lifecycle -- not a second source of truth. LangGraph's own
checkpointed state remains authoritative for what a workflow may do next
(resume, routing); these methods only let a review queue find candidate
cases without scanning/deserializing checkpoint history. Callers (the HTTP
routers) write this projection immediately after observing the same
outcome from ``graph.ainvoke`` that the workflow itself already produced --
never as an independent decision.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from aegis.models.clinical_note import ClinicalNote

_INITIAL_CASE_STATUS = "pending_ai"
_PENDING_REVIEW_STATUS = "pending_hitl"
_ARCHIVED_STATUS = "archived"


@dataclass(frozen=True)
class PendingReviewCase:
    """
    One row of the review queue projection.

    A read model over ``patient_case``, not a runtime domain contract
    artifact -- it exists solely to let a queue listing be built from a
    cheap SQL query instead of enumerating LangGraph checkpoints.
    """

    case_id: UUID
    patient_id: UUID
    workflow_id: UUID
    submitted_at: datetime


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

    def mark_pending_review(self, case_id: UUID) -> None:
        """Project that ``case_id``'s workflow is suspended awaiting physician review."""
        self._update_status(case_id, _PENDING_REVIEW_STATUS)

    def mark_archived(self, case_id: UUID) -> None:
        """Project that ``case_id``'s workflow has reached a terminal ``ClinicalDecision``."""
        self._update_status(case_id, _ARCHIVED_STATUS)

    def _update_status(self, case_id: UUID, status: str) -> None:
        try:
            self._conn.execute(
                "UPDATE patient_case SET status = ? WHERE case_id = ?;",
                (status, str(case_id)),
            )
            self._conn.commit()
        except sqlite3.Error:
            self._conn.rollback()
            raise

    def list_pending_review(self) -> list[PendingReviewCase]:
        """
        Cases currently suspended at ``human_review_pending``, oldest first.

        Reads only the ``status`` projection maintained by
        ``mark_pending_review``/``mark_archived`` -- never inspects or
        deserializes LangGraph checkpoint state.
        """
        rows = self._conn.execute(
            """
            SELECT case_id, patient_id, thread_id, ingress_timestamp
            FROM patient_case
            WHERE status = ?
            ORDER BY ingress_timestamp ASC;
            """,
            (_PENDING_REVIEW_STATUS,),
        ).fetchall()

        return [
            PendingReviewCase(
                case_id=UUID(row["case_id"]),
                patient_id=UUID(row["patient_id"]),
                workflow_id=UUID(row["thread_id"]),
                submitted_at=datetime.fromisoformat(row["ingress_timestamp"]),
            )
            for row in rows
        ]
