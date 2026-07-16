from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from aegis.infrastructure.sqlite.clinical_decision_repository import (
    SQLiteClinicalDecisionRepository,
)
from aegis.models.clinical_decision import (
    ApprovedICDClassification,
    ClinicalDecision,
    RecommendationDisposition,
)


def _seed_case_and_codes(conn: sqlite3.Connection, case_id: UUID, patient_id: UUID) -> None:
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
    for code in ("1A00", "1A01", "1A02"):
        conn.execute(
            "INSERT INTO icd11_taxonomy (code, title, class_kind) VALUES (?, ?, 'category');",
            (code, f"Condition {code}"),
        )
    conn.commit()


def _build_clinical_decision(case_id: UUID, patient_id: UUID) -> ClinicalDecision:
    return ClinicalDecision(
        decision_id=uuid4(),
        case_id=case_id,
        patient_id_reference=patient_id,
        approved_icd_codes=[
            ApprovedICDClassification(
                icd_code="1A00", disposition=RecommendationDisposition.ACCEPTED
            ),
            ApprovedICDClassification(icd_code="1A01", disposition=RecommendationDisposition.ADDED),
            ApprovedICDClassification(
                icd_code="1A02", disposition=RecommendationDisposition.MODIFIED
            ),
        ],
        normalization_version="1.0",
        created_at=datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc),
    )


def test_round_trip_persistence(clinical_db_connection: sqlite3.Connection) -> None:
    case_id, patient_id = uuid4(), uuid4()
    _seed_case_and_codes(clinical_db_connection, case_id, patient_id)
    decision = _build_clinical_decision(case_id, patient_id)

    repository = SQLiteClinicalDecisionRepository(clinical_db_connection)
    repository.save(decision)
    retrieved = repository.get_by_decision_id(decision.decision_id)

    assert retrieved == decision


def test_round_trip_preserves_approved_code_order_and_disposition(
    clinical_db_connection: sqlite3.Connection,
) -> None:
    case_id, patient_id = uuid4(), uuid4()
    _seed_case_and_codes(clinical_db_connection, case_id, patient_id)
    decision = _build_clinical_decision(case_id, patient_id)

    repository = SQLiteClinicalDecisionRepository(clinical_db_connection)
    repository.save(decision)
    retrieved = repository.get_by_decision_id(decision.decision_id)

    assert retrieved is not None
    assert [c.icd_code for c in retrieved.approved_icd_codes] == ["1A00", "1A01", "1A02"]
    assert [c.disposition for c in retrieved.approved_icd_codes] == [
        RecommendationDisposition.ACCEPTED,
        RecommendationDisposition.ADDED,
        RecommendationDisposition.MODIFIED,
    ]


def test_get_by_decision_id_returns_none_when_absent(
    clinical_db_connection: sqlite3.Connection,
) -> None:
    repository = SQLiteClinicalDecisionRepository(clinical_db_connection)

    assert repository.get_by_decision_id(uuid4()) is None


def test_save_rejects_unknown_case_with_clear_failure(
    clinical_db_connection: sqlite3.Connection,
) -> None:
    """Foreign-key violations (unknown case/patient/ICD code) must propagate, not corrupt state."""
    decision = _build_clinical_decision(case_id=uuid4(), patient_id=uuid4())
    repository = SQLiteClinicalDecisionRepository(clinical_db_connection)

    with pytest.raises(sqlite3.IntegrityError):
        repository.save(decision)

    assert repository.get_by_decision_id(decision.decision_id) is None


def test_save_is_atomic_across_decision_and_classification_tables(
    clinical_db_connection: sqlite3.Connection,
) -> None:
    """A failure partway through (bad ICD code) must not leave a dangling decision row behind."""
    case_id, patient_id = uuid4(), uuid4()
    _seed_case_and_codes(clinical_db_connection, case_id, patient_id)
    decision = ClinicalDecision(
        decision_id=uuid4(),
        case_id=case_id,
        patient_id_reference=patient_id,
        approved_icd_codes=[
            ApprovedICDClassification(
                icd_code="1A00", disposition=RecommendationDisposition.ACCEPTED
            ),
            ApprovedICDClassification(
                icd_code="UNKNOWN99", disposition=RecommendationDisposition.ADDED
            ),
        ],
        normalization_version="1.0",
        created_at=datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc),
    )
    repository = SQLiteClinicalDecisionRepository(clinical_db_connection)

    with pytest.raises(sqlite3.IntegrityError):
        repository.save(decision)

    assert repository.get_by_decision_id(decision.decision_id) is None
    row = clinical_db_connection.execute(
        "SELECT COUNT(*) as count FROM clinical_decision WHERE decision_id = ?;",
        (str(decision.decision_id),),
    ).fetchone()
    assert row["count"] == 0


def test_round_trip_result_is_a_domain_model_not_a_raw_row(
    clinical_db_connection: sqlite3.Connection,
) -> None:
    case_id, patient_id = uuid4(), uuid4()
    _seed_case_and_codes(clinical_db_connection, case_id, patient_id)
    decision = _build_clinical_decision(case_id, patient_id)
    repository = SQLiteClinicalDecisionRepository(clinical_db_connection)
    repository.save(decision)

    retrieved = repository.get_by_decision_id(decision.decision_id)

    assert isinstance(retrieved, ClinicalDecision)
    assert not isinstance(retrieved, sqlite3.Row)
    assert not isinstance(retrieved, dict)
