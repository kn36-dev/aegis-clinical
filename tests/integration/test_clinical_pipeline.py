# End-to-end clinical pipeline: submission -> normalization -> cache
# lookup -> retrieval -> AI reasoning -> human review interrupt ->
# physician decision resume -> persistence -> cache projection, driven
# entirely through the real FastAPI HTTP boundary (the real app, real
# lifespan, real LangGraph graph and checkpointer). Every collaborator
# that would otherwise require Groq/Upstash credentials is substituted
# with a fake via ``build_container``'s injectable parameters, so this
# test never makes a network call.
from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from aegis.application.container import build_container
from aegis.database.database import init_clinical_database
from tests.application.fakes import (
    KNOWN_ICD_CODE,
    FakeClinicalDecisionCacheRepository,
    FakeContentRepository,
    FakeEmbeddingProvider,
    FakeICDCodeValidator,
    FakePHIAnonymizer,
    FakeReasoningProvider,
    FakeVectorQueryProvider,
)

if TYPE_CHECKING:
    from pathlib import Path


SAMPLE_NOTE_TEXT = (
    "Patient presents with acute watery diarrhea and mild dehydration. "
    "No fever. No blood in stool. Onset 12 hours ago."
)


def _seed_icd_taxonomy(connection: sqlite3.Connection, icd_code: str) -> None:
    """
    Register the ICD-11 code physician review will select.

    ``approved_icd_classification.icd_code`` has a foreign key onto
    ``icd11_taxonomy(code)`` (migration 0012). In production this table is
    pre-loaded from the canonical ICD-11 taxonomy (``make db-seed-icd``);
    ``FakeICDCodeValidator`` only substitutes for the not-yet-implemented
    validator service and never touches this table, so the real taxonomy
    row must exist here too, mirroring
    ``tests/infrastructure/sqlite/test_clinical_decision_repository.py``.
    """
    connection.execute(
        "INSERT INTO icd11_taxonomy (code, title, class_kind) VALUES (?, ?, 'category');",
        (icd_code, f"Condition {icd_code}"),
    )
    connection.commit()


def _seed_patient_identity(connection: sqlite3.Connection, patient_id: UUID) -> None:
    """
    Register a patient identity ahead of note submission.

    ``patient_case.patient_id`` has a foreign key onto
    ``patient_identity_vault`` (migration 0002): per
    ``runtime_domain_contracts/clinical_note.md``, AEGIS assumes patient
    identity already exists in an external identity system, so every
    ``patient_id`` this test submits must be seeded here first, mirroring
    ``tests/infrastructure/sqlite/test_clinical_note_repository.py``.
    """
    connection.execute(
        """
        INSERT INTO patient_identity_vault (
            patient_id, medical_record_number, first_name, last_name, date_of_birth
        ) VALUES (?, ?, ?, ?, ?);
        """,
        (str(patient_id), f"MRN-{patient_id}", "Jane", "Doe", "1990-01-01"),
    )
    connection.commit()


class _FakeSettings:
    GRAPH_CHECKPOINT_DB_PATH: str
    RETRIEVAL_TOP_K = 3
    RETRIEVAL_SIMILARITY_THRESHOLD = None

    def __init__(self, graph_checkpoint_db_path: str) -> None:
        self.GRAPH_CHECKPOINT_DB_PATH = graph_checkpoint_db_path


@pytest.fixture
def demo_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[TestClient, str, sqlite3.Connection]]:
    import aegis.api.main as main_module

    content_reference = f"content-store://clinical-notes/{uuid4()}"

    db_path = tmp_path / "clinical_registry.db"
    init_clinical_database(db_path)
    connection = sqlite3.connect(db_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON;")
    _seed_icd_taxonomy(connection, KNOWN_ICD_CODE)

    container = build_container(
        connection,
        cache_repository=FakeClinicalDecisionCacheRepository(),
        embedding_provider=FakeEmbeddingProvider(),
        vector_query_provider=FakeVectorQueryProvider(),
        reasoning_provider=FakeReasoningProvider(),
        reasoning_model_name="fake-model",
        icd_code_validator=FakeICDCodeValidator(),
        phi_anonymizer=FakePHIAnonymizer(),
        content_repository=FakeContentRepository(
            content_by_reference={content_reference: SAMPLE_NOTE_TEXT}
        ),
    )
    settings = _FakeSettings(str(tmp_path / "graph_checkpoints.db"))

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "open_clinical_connection", lambda _settings: connection)
    monkeypatch.setattr(main_module, "build_infrastructure", lambda _settings, _conn: container)

    with TestClient(main_module.app) as client:
        yield client, content_reference, connection

    connection.close()


def test_full_note_lifecycle_submit_review_decision(
    demo_client: tuple[TestClient, str, sqlite3.Connection],
) -> None:
    client, content_reference, connection = demo_client
    patient_id = uuid4()
    _seed_patient_identity(connection, patient_id)

    submit_response = client.post(
        "/api/v1/clinical-notes",
        json={"patient_id": str(patient_id), "content_reference": content_reference},
    )
    assert submit_response.status_code == 202
    submit_body = submit_response.json()
    assert submit_body["status"] == "pending_review"
    assert submit_body["decision_id"] is None
    workflow_id = submit_body["workflow_id"]
    case_id = submit_body["case_id"]

    pending_review = client.get(f"/api/v1/reviews/{workflow_id}")
    assert pending_review.status_code == 200
    pending_body = pending_review.json()
    assert pending_body["status"] == "pending_review"
    assert pending_body["case_id"] == case_id
    assert pending_body["recommended_icd_codes"][0]["icd_code"] == KNOWN_ICD_CODE
    assert pending_body["normalized_note_text"]

    decision_response = client.post(
        f"/api/v1/reviews/{workflow_id}/decision",
        json={"selected_icd_codes": [KNOWN_ICD_CODE]},
    )
    assert decision_response.status_code == 200
    decision_body = decision_response.json()
    assert decision_body["case_id"] == case_id
    assert decision_body["decision_id"] is not None
    assert decision_body["approved_icd_codes"][0]["icd_code"] == KNOWN_ICD_CODE

    completed_review = client.get(f"/api/v1/reviews/{workflow_id}")
    completed_body = completed_review.json()
    assert completed_body["status"] == "completed"
    assert completed_body["decision_id"] == decision_body["decision_id"]


def test_repeat_submission_with_same_content_hits_cache(
    demo_client: tuple[TestClient, str, sqlite3.Connection],
) -> None:
    client, content_reference, connection = demo_client

    first_patient_id = uuid4()
    _seed_patient_identity(connection, first_patient_id)
    first_submit = client.post(
        "/api/v1/clinical-notes",
        json={"patient_id": str(first_patient_id), "content_reference": content_reference},
    )
    assert first_submit.status_code == 202
    first_workflow_id = first_submit.json()["workflow_id"]

    first_decision = client.post(
        f"/api/v1/reviews/{first_workflow_id}/decision",
        json={"selected_icd_codes": [KNOWN_ICD_CODE]},
    )
    assert first_decision.status_code == 200
    first_decision_id = first_decision.json()["decision_id"]

    second_patient_id = uuid4()
    _seed_patient_identity(connection, second_patient_id)
    second_submit = client.post(
        "/api/v1/clinical-notes",
        json={"patient_id": str(second_patient_id), "content_reference": content_reference},
    )
    assert second_submit.status_code == 201
    second_body = second_submit.json()
    assert second_body["status"] == "completed"
    assert second_body["decision_id"] == first_decision_id
    assert second_body["approved_icd_codes"][0]["icd_code"] == KNOWN_ICD_CODE
