"""
SQLiteContentStore

Concrete SQLite adapter for the ``ClinicalNoteContentRepository`` protocol
(``aegis.services.normalization_service``).

This is a Content Storage Provider implementation, not the abstraction
itself: ``ClinicalNoteContentRepository`` is the stable boundary
``NormalizationService`` depends on, and ``SQLiteContentStore`` is today's
concrete provider behind it. A future provider (e.g. an
``EncryptedClinicalContentStore``) can replace this class without
``NormalizationService`` changing. This implementation stores
``content_payload`` as plaintext -- no encryption is assumed, implemented,
or simulated here.

Owns SQL execution, serialization, and integrity checking (a checksum
computed over the stored payload) only -- no PHI anonymization, no
clinical interpretation.
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from uuid import UUID


class ContentNotFoundError(LookupError):
    """Raised when no content is stored for the given ``content_reference``."""


class ContentIntegrityError(RuntimeError):
    """
    Raised when stored content fails its checksum verification on read.

    Signals storage-layer corruption rather than a business-rule failure;
    it must never be silently swallowed.
    """


class SQLiteContentStore:
    """
    ``ClinicalNoteContentRepository`` implementation backed by the clinical
    registry SQLite database (``clinical_note_content`` table, migration
    0009).

    Structurally satisfies
    ``aegis.services.normalization_service.ClinicalNoteContentRepository``
    (``get_content``). ``save_content`` is an additional capability beyond
    that protocol -- ``NormalizationService`` never writes content, so this
    exists for adapter-level seeding/testing and future ingress-layer use.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection

    def get_content(self, content_reference: str) -> str:
        row = self._conn.execute(
            """
            SELECT content_payload, checksum
            FROM clinical_note_content
            WHERE content_reference = ?;
            """,
            (content_reference,),
        ).fetchone()

        if row is None:
            raise ContentNotFoundError(
                f"No stored content for content_reference={content_reference!r}"
            )

        content_payload = row["content_payload"]

        if not isinstance(content_payload, str):
            raise ContentIntegrityError(
                f"Stored content payload is not text for content_reference={content_reference!r}"
            )

        if self._checksum_of(content_payload) != row["checksum"]:
            raise ContentIntegrityError(
                f"Checksum mismatch for content_reference={content_reference!r}"
            )

        return content_payload

    def save_content(self, case_id: UUID, content_reference: str, content_payload: str) -> None:
        """Adapter-only write path, used to seed content ahead of a get_content() call."""
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO clinical_note_content (
                    content_reference,
                    case_id,
                    content_payload,
                    checksum,
                    created_at
                ) VALUES (?, ?, ?, ?, ?);
                """,
                (
                    content_reference,
                    str(case_id),
                    content_payload,
                    self._checksum_of(content_payload),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            self._conn.commit()
        except sqlite3.Error:
            self._conn.rollback()
            raise

    @staticmethod
    def _checksum_of(content_payload: str) -> str:
        return hashlib.sha256(content_payload.encode("utf-8")).hexdigest()
