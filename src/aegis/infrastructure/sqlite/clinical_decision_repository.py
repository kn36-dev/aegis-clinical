"""
SQLiteClinicalDecisionRepository

Concrete SQLite adapter for the ``ClinicalDecisionRepository`` protocol
(``aegis.services.persistence_service``).

Maps the immutable, physician-approved ``ClinicalDecision`` domain artifact
onto two tables: ``clinical_decision`` (decision-level fields) and
``approved_icd_classification`` (one row per ``ApprovedICDClassification``,
migrations 0011/0012). Deliberately separate from ``patient_extracted_code``
(migration 0004), which is shaped for AI-extraction predictions
(confidence_score, extraction_source) that ``ClinicalDecision``'s domain
contract explicitly excludes -- this repository never fabricates those
fields to fit the older table.

Owns SQL execution, serialization, and persistence mapping only -- no
clinical validation, no recommendation evaluation, no workflow routing;
those belong to ``ClinicalDecisionService`` and the workflow orchestration
layer.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from uuid import UUID

from aegis.models.clinical_decision import (
    ApprovedICDClassification,
    ClinicalDecision,
    RecommendationDisposition,
)


class SQLiteClinicalDecisionRepository:
    """
    ``ClinicalDecisionRepository`` implementation backed by the clinical
    registry SQLite database.

    Structurally satisfies
    ``aegis.services.persistence_service.ClinicalDecisionRepository``
    (``save``). ``get_by_decision_id`` is an additional capability beyond
    that protocol, provided for independent adapter verification
    (round-trip testing).
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection

    def save(self, clinical_decision: ClinicalDecision) -> None:
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO clinical_decision (
                    decision_id,
                    case_id,
                    patient_id_reference,
                    normalization_version,
                    created_at
                ) VALUES (?, ?, ?, ?, ?);
                """,
                (
                    str(clinical_decision.decision_id),
                    str(clinical_decision.case_id),
                    str(clinical_decision.patient_id_reference),
                    clinical_decision.normalization_version,
                    clinical_decision.created_at.isoformat(),
                ),
            )

            cursor.executemany(
                """
                INSERT INTO approved_icd_classification (
                    decision_id,
                    icd_code,
                    disposition,
                    sequence_index
                ) VALUES (?, ?, ?, ?);
                """,
                [
                    (
                        str(clinical_decision.decision_id),
                        classification.icd_code,
                        classification.disposition.value,
                        sequence_index,
                    )
                    for sequence_index, classification in enumerate(
                        clinical_decision.approved_icd_codes
                    )
                ],
            )

            self._conn.commit()
        except sqlite3.Error:
            self._conn.rollback()
            raise

    def get_by_decision_id(self, decision_id: UUID) -> ClinicalDecision | None:
        """Adapter-only read path, used by tests to verify round-trip fidelity."""
        decision_row = self._conn.execute(
            """
            SELECT decision_id, case_id, patient_id_reference, normalization_version, created_at
            FROM clinical_decision
            WHERE decision_id = ?;
            """,
            (str(decision_id),),
        ).fetchone()

        if decision_row is None:
            return None

        classification_rows = self._conn.execute(
            """
            SELECT icd_code, disposition
            FROM approved_icd_classification
            WHERE decision_id = ?
            ORDER BY sequence_index;
            """,
            (str(decision_id),),
        ).fetchall()

        return ClinicalDecision(
            decision_id=UUID(decision_row["decision_id"]),
            case_id=UUID(decision_row["case_id"]),
            patient_id_reference=UUID(decision_row["patient_id_reference"]),
            approved_icd_codes=[
                ApprovedICDClassification(
                    icd_code=row["icd_code"],
                    disposition=RecommendationDisposition(row["disposition"]),
                )
                for row in classification_rows
            ],
            normalization_version=decision_row["normalization_version"],
            created_at=datetime.fromisoformat(decision_row["created_at"]),
        )
