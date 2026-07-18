# tests/api/test_clinical_router.py
"""
Router-level tests for POST /api/v1/clinical-notes.

Exercises ``aegis.api.routers.clinical`` against a fake compiled graph
(via ``app.dependency_overrides[get_graph]``) rather than the real AEGIS
workflow -- these tests prove the HTTP adapter's translation behavior,
not workflow or service correctness (that's covered by
``tests/graphs/test_workflow_integration.py`` and
``tests/application/test_dependency_substitution.py``). No SQLite,
Redis, Upstash Vector, or LLM is ever touched.
"""

from __future__ import annotations

import ast
import inspect
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from aegis.api.dependencies import get_container, get_graph
from aegis.api.routers import clinical
from aegis.models.clinical_decision import (
    ApprovedICDClassification,
    ClinicalDecision,
    RecommendationDisposition,
)
from aegis.models.clinical_note import ClinicalNote

FIXED_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


class FakeCompiledGraph:
    """Stands in for the real LangGraph ``CompiledStateGraph`` on ``app.state.graph``."""

    def __init__(
        self, result: dict[str, Any] | None = None, error: Exception | None = None
    ) -> None:
        self._result = result
        self._error = error
        self.calls: list[dict[str, Any]] = []

    async def ainvoke(self, state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"state": state, "config": config})
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


class FakeClinicalNoteService:
    """
    Records ``create_clinical_note`` calls
    -- stands in for ``AegisContainer.clinical_note_service``.
    """

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create_clinical_note(self, submission: Any, case_id: Any = None) -> None:
        self.calls.append({"submission": submission, "case_id": case_id})


class FakeIngestContentRepository:
    """Records ``save_content`` calls -- stands in for ``AegisContainer.content_repository``."""

    def __init__(self) -> None:
        self.saved: list[dict[str, Any]] = []

    def get_content(self, content_reference: str) -> str:
        raise NotImplementedError("ingest_clinical_note never reads content back")

    def save_content(self, case_id: Any, content_reference: str, content_payload: str) -> None:
        self.saved.append(
            {
                "case_id": case_id,
                "content_reference": content_reference,
                "content_payload": content_payload,
            }
        )


class FakeContainer:
    """Minimal stand-in for ``AegisContainer`` -- only the two fields the ingest route touches."""

    def __init__(
        self,
        clinical_note_service: FakeClinicalNoteService,
        content_repository: FakeIngestContentRepository,
    ) -> None:
        self.clinical_note_service = clinical_note_service
        self.content_repository = content_repository


def make_app(fake_graph: FakeCompiledGraph, container: Any = None) -> FastAPI:
    app = FastAPI()
    app.include_router(clinical.router, prefix="/api/v1")
    app.dependency_overrides[get_graph] = lambda: fake_graph
    if container is not None:
        app.dependency_overrides[get_container] = lambda: container
    return app


def make_payload() -> dict[str, Any]:
    return {
        "patient_id": str(uuid4()),
        "content_reference": "content-store://clinical-notes/abc123",
    }


def make_ingest_payload() -> dict[str, Any]:
    return {
        "patient_id": str(uuid4()),
        "note_text": "Patient reports no fever. Mild cough.",
    }


def test_successful_submission_reaches_graph_with_submission_and_thread_id() -> None:
    decision = ClinicalDecision(
        decision_id=uuid4(),
        case_id=uuid4(),
        patient_id_reference=uuid4(),
        approved_icd_codes=[
            ApprovedICDClassification(
                icd_code="1A00", disposition=RecommendationDisposition.ACCEPTED
            )
        ],
        normalization_version="1.0",
        created_at=FIXED_TIME,
    )
    fake_graph = FakeCompiledGraph(result={"clinical_decision": decision})
    client = TestClient(make_app(fake_graph))
    payload = make_payload()

    response = client.post("/api/v1/clinical-notes", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["decision_id"] == str(decision.decision_id)
    assert body["case_id"] == str(decision.case_id)
    assert body["approved_icd_codes"] == [{"icd_code": "1A00", "disposition": "accepted"}]

    assert len(fake_graph.calls) == 1
    invoked_state = fake_graph.calls[0]["state"]
    assert str(invoked_state["submission"].patient_id) == payload["patient_id"]
    assert invoked_state["submission"].content_reference == payload["content_reference"]
    assert "thread_id" in fake_graph.calls[0]["config"]["configurable"]


def test_router_does_not_import_application_services_directly() -> None:
    source = inspect.getsource(clinical)
    tree = ast.parse(source)

    imported_modules = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    }

    forbidden_imports = [
        "aegis.services.clinical_note_service",
        "aegis.services.normalization_service",
        "aegis.services.retrieval_service",
        "aegis.services.cache_service",
        "aegis.repositories",
    ]

    for forbidden in forbidden_imports:
        assert forbidden not in imported_modules, f"router must not import {forbidden!r} directly"


def test_pending_review_state_returned_correctly() -> None:
    clinical_note = ClinicalNote(
        case_id=uuid4(),
        patient_id=uuid4(),
        content_reference="content-store://clinical-notes/abc123",
        created_at=FIXED_TIME,
    )
    fake_graph = FakeCompiledGraph(
        result={"clinical_note": clinical_note, "__interrupt__": ("pending",)}
    )
    client = TestClient(make_app(fake_graph))

    response = client.post("/api/v1/clinical-notes", json=make_payload())

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending_review"
    assert body["case_id"] == str(clinical_note.case_id)
    assert body["decision_id"] is None
    assert body["approved_icd_codes"] is None


def test_graph_invocation_failure_translated_without_leaking_internals() -> None:
    fake_graph = FakeCompiledGraph(error=RuntimeError("sqlite3.OperationalError: disk I/O error"))
    client = TestClient(make_app(fake_graph))

    response = client.post("/api/v1/clinical-notes", json=make_payload())

    assert response.status_code == 502
    body = response.json()
    assert "disk I/O error" not in body["detail"]
    assert body["detail"] == "Clinical workflow execution failed."


def test_invalid_submission_is_rejected_before_reaching_graph() -> None:
    fake_graph = FakeCompiledGraph(result={"clinical_decision": None})
    client = TestClient(make_app(fake_graph))

    response = client.post("/api/v1/clinical-notes", json={"patient_id": str(uuid4())})

    assert response.status_code == 422
    assert fake_graph.calls == []


def test_ingest_persists_clinical_note_then_seeds_content_then_invokes_graph() -> None:
    """
    The three collaborators must run in this exact order: the patient_case
    row (via clinical_note_service) has to exist before content_repository
    can store content against it (clinical_note_content's FK), and both
    must happen before the graph runs.
    """
    decision = ClinicalDecision(
        decision_id=uuid4(),
        case_id=uuid4(),
        patient_id_reference=uuid4(),
        approved_icd_codes=[
            ApprovedICDClassification(
                icd_code="1A00", disposition=RecommendationDisposition.ACCEPTED
            )
        ],
        normalization_version="1.0",
        created_at=FIXED_TIME,
    )
    fake_graph = FakeCompiledGraph(result={"clinical_decision": decision})
    note_service = FakeClinicalNoteService()
    content_repository = FakeIngestContentRepository()
    container = FakeContainer(note_service, content_repository)
    client = TestClient(make_app(fake_graph, container=container))
    payload = make_ingest_payload()

    response = client.post("/api/v1/clinical-notes/ingest", json=payload)

    assert response.status_code == 201

    assert len(note_service.calls) == 1
    minted_submission = note_service.calls[0]["submission"]
    minted_case_id = note_service.calls[0]["case_id"]
    assert str(minted_submission.patient_id) == payload["patient_id"]
    assert minted_case_id is not None

    assert len(content_repository.saved) == 1
    seeded = content_repository.saved[0]
    assert seeded["case_id"] == minted_case_id
    assert seeded["content_payload"] == payload["note_text"]
    assert seeded["content_reference"] == minted_submission.content_reference

    assert len(fake_graph.calls) == 1
    invoked_state = fake_graph.calls[0]["state"]
    assert invoked_state["case_id"] == minted_case_id
    assert invoked_state["submission"].content_reference == minted_submission.content_reference


def test_ingest_rejects_blank_note_text_before_touching_anything() -> None:
    fake_graph = FakeCompiledGraph(result={"clinical_decision": None})
    note_service = FakeClinicalNoteService()
    content_repository = FakeIngestContentRepository()
    container = FakeContainer(note_service, content_repository)
    client = TestClient(make_app(fake_graph, container=container))

    response = client.post(
        "/api/v1/clinical-notes/ingest",
        json={"patient_id": str(uuid4()), "note_text": ""},
    )

    assert response.status_code == 422
    assert note_service.calls == []
    assert content_repository.saved == []
    assert fake_graph.calls == []
