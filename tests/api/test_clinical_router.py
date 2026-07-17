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

from aegis.api.dependencies import get_graph
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


def make_app(fake_graph: FakeCompiledGraph) -> FastAPI:
    app = FastAPI()
    app.include_router(clinical.router, prefix="/api/v1")
    app.dependency_overrides[get_graph] = lambda: fake_graph
    return app


def make_payload() -> dict[str, Any]:
    return {
        "patient_id": str(uuid4()),
        "content_reference": "content-store://clinical-notes/abc123",
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
