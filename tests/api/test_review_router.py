# tests/api/test_review_router.py
"""
Router-level tests for GET /api/v1/reviews/{thread_id} and
POST /api/v1/reviews/{thread_id}/decision.

Exercises ``aegis.api.routers.review`` against a fake compiled graph (via
``app.dependency_overrides[get_graph]``) rather than the real AEGIS
workflow -- these tests prove the HTTP adapter's translation behavior,
not workflow or service correctness (that's covered by
``tests/graphs/test_workflow_integration.py``). No SQLite, Redis, Upstash
Vector, or LLM is ever touched.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langgraph.types import Command, Interrupt

from aegis.api.dependencies import get_graph
from aegis.api.routers import review
from aegis.models.clinical_decision import (
    ApprovedICDClassification,
    ClinicalDecision,
    RecommendationDisposition,
)
from aegis.models.clinical_note import ClinicalNote
from aegis.models.coding_recommendation import (
    CodingRecommendation,
    EvidenceReference,
    ICDCodeRecommendation,
    ReasoningMetadata,
)
from aegis.models.normalized_clinical_note import NormalizedClinicalNote
from aegis.services.clinical_decision_service import PhysicianDecisionSubmission
from aegis.services.clinical_note_service import ClinicalNoteSubmission

FIXED_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


@dataclass
class FakeStateSnapshot:
    """Stands in for the fields of LangGraph's ``StateSnapshot`` this router reads."""

    values: dict[str, Any]
    interrupts: tuple[Interrupt, ...] = ()


@dataclass
class FakeCompiledGraph:
    """Stands in for the real LangGraph ``CompiledStateGraph`` on ``app.state.graph``."""

    snapshot: FakeStateSnapshot | None = None
    snapshot_error: Exception | None = None
    invoke_result: dict[str, Any] | None = None
    invoke_error: Exception | None = None
    state_calls: list[dict[str, Any]] = field(default_factory=list)
    invoke_calls: list[dict[str, Any]] = field(default_factory=list)

    async def aget_state(self, config: dict[str, Any]) -> FakeStateSnapshot:
        self.state_calls.append(config)
        if self.snapshot_error is not None:
            raise self.snapshot_error
        assert self.snapshot is not None
        return self.snapshot

    async def ainvoke(self, command: Any, config: dict[str, Any]) -> dict[str, Any]:
        self.invoke_calls.append({"command": command, "config": config})
        if self.invoke_error is not None:
            raise self.invoke_error
        assert self.invoke_result is not None
        return self.invoke_result


def make_app(fake_graph: FakeCompiledGraph) -> FastAPI:
    app = FastAPI()
    app.include_router(review.router, prefix="/api/v1/reviews")
    app.dependency_overrides[get_graph] = lambda: fake_graph
    return app


def make_submission() -> ClinicalNoteSubmission:
    return ClinicalNoteSubmission(
        patient_id=uuid4(),
        content_reference="content-store://clinical-notes/abc123",
    )


def make_pending_snapshot() -> tuple[FakeStateSnapshot, dict[str, Any]]:
    submission = make_submission()
    case_id = uuid4()
    recommendation_id = uuid4()
    clinical_note = ClinicalNote(
        case_id=case_id,
        patient_id=submission.patient_id,
        content_reference=submission.content_reference,
        created_at=FIXED_TIME,
    )
    normalized_note = NormalizedClinicalNote(
        clinical_note=clinical_note,
        normalized_text="anonymized note text",
        normalization_version="1.0",
        created_at=FIXED_TIME,
    )
    coding_recommendation = CodingRecommendation(
        recommendation_id=recommendation_id,
        case_id=case_id,
        recommendations=[
            ICDCodeRecommendation(
                icd_code="1A00",
                supporting_findings=["mild cough"],
                conflicting_findings=[],
                justification="Consistent with reported findings.",
                model_confidence=0.8,
            )
        ],
        reasoning_summary="Findings are consistent with cholera.",
        evidence_reference=EvidenceReference(candidate_icd_codes=["1A00"]),
        metadata=ReasoningMetadata(
            model_name="fake-model",
            prompt_version="test",
            temperature=0.0,
            generated_at=FIXED_TIME,
        ),
    )
    values = {
        "submission": submission,
        "clinical_note": clinical_note,
        "normalized_note": normalized_note,
        "coding_recommendation": coding_recommendation,
    }
    snapshot = FakeStateSnapshot(
        values=values,
        interrupts=(Interrupt(value={"coding_recommendation": coding_recommendation}),),
    )
    return snapshot, values


def make_decision(submission: PhysicianDecisionSubmission) -> ClinicalDecision:
    return ClinicalDecision(
        decision_id=uuid4(),
        case_id=submission.case_id,
        patient_id_reference=submission.patient_id_reference,
        approved_icd_codes=[
            ApprovedICDClassification(icd_code=code, disposition=RecommendationDisposition.ACCEPTED)
            for code in submission.selected_icd_codes
        ],
        normalization_version=submission.normalization_version,
        created_at=FIXED_TIME,
    )


def test_get_pending_review_returns_recommendation_state() -> None:
    snapshot, values = make_pending_snapshot()
    fake_graph = FakeCompiledGraph(snapshot=snapshot)
    client = TestClient(make_app(fake_graph))
    thread_id = uuid4()

    response = client.get(f"/api/v1/reviews/{thread_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending_review"
    assert body["case_id"] == str(values["coding_recommendation"].case_id)
    assert body["recommendation_id"] == str(values["coding_recommendation"].recommendation_id)
    assert body["reasoning_summary"] == "Findings are consistent with cholera."
    assert body["normalized_note_text"] == "anonymized note text"
    assert body["recommended_icd_codes"] == [
        {
            "icd_code": "1A00",
            "justification": "Consistent with reported findings.",
            "model_confidence": 0.8,
            "supporting_findings": ["mild cough"],
            "conflicting_findings": [],
        }
    ]
    assert body["decision_id"] is None
    assert body["approved_icd_codes"] is None
    assert fake_graph.state_calls[0]["configurable"]["thread_id"] == str(thread_id)


def test_get_completed_review_returns_completed_state() -> None:
    _, values = make_pending_snapshot()
    submission = PhysicianDecisionSubmission(
        case_id=values["coding_recommendation"].case_id,
        recommendation_id=values["coding_recommendation"].recommendation_id,
        patient_id_reference=values["submission"].patient_id,
        normalization_version=values["normalized_note"].normalization_version,
        selected_icd_codes=["1A00"],
    )
    decision = make_decision(submission)
    fake_graph = FakeCompiledGraph(
        snapshot=FakeStateSnapshot(values={"clinical_decision": decision})
    )
    client = TestClient(make_app(fake_graph))

    response = client.get(f"/api/v1/reviews/{uuid4()}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["decision_id"] == str(decision.decision_id)
    assert body["approved_icd_codes"] == [{"icd_code": "1A00", "disposition": "accepted"}]
    assert body["recommendation_id"] is None


def test_get_unknown_thread_returns_404() -> None:
    fake_graph = FakeCompiledGraph(snapshot=FakeStateSnapshot(values={}))
    client = TestClient(make_app(fake_graph))

    response = client.get(f"/api/v1/reviews/{uuid4()}")

    assert response.status_code == 404


def test_get_state_failure_translated_without_leaking_internals() -> None:
    fake_graph = FakeCompiledGraph(
        snapshot_error=RuntimeError("sqlite3.OperationalError: disk I/O error")
    )
    client = TestClient(make_app(fake_graph))

    response = client.get(f"/api/v1/reviews/{uuid4()}")

    assert response.status_code == 502
    assert "disk I/O error" not in response.json()["detail"]


def test_post_decision_resumes_graph_with_state_derived_submission() -> None:
    snapshot, values = make_pending_snapshot()
    thread_id = uuid4()

    # The router builds this exact submission from the pending snapshot's
    # state plus the request body -- computed here, independently of the
    # router, so the test doesn't just echo the implementation back.
    expected_submission = PhysicianDecisionSubmission(
        case_id=values["coding_recommendation"].case_id,
        recommendation_id=values["coding_recommendation"].recommendation_id,
        patient_id_reference=values["submission"].patient_id,
        normalization_version=values["normalized_note"].normalization_version,
        selected_icd_codes=["1A00"],
    )
    decision = make_decision(expected_submission)
    fake_graph = FakeCompiledGraph(
        snapshot=snapshot,
        invoke_result={"clinical_decision": decision},
    )
    client = TestClient(make_app(fake_graph))

    response = client.post(
        f"/api/v1/reviews/{thread_id}/decision",
        json={"selected_icd_codes": ["1A00"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision_id"] is not None
    assert body["approved_icd_codes"] == [{"icd_code": "1A00", "disposition": "accepted"}]

    assert len(fake_graph.invoke_calls) == 1
    resumed_command = fake_graph.invoke_calls[0]["command"]
    assert isinstance(resumed_command, Command)
    resumed_submission = resumed_command.resume
    assert isinstance(resumed_submission, PhysicianDecisionSubmission)
    assert resumed_submission.case_id == values["coding_recommendation"].case_id
    assert resumed_submission.recommendation_id == values["coding_recommendation"].recommendation_id
    assert resumed_submission.patient_id_reference == values["submission"].patient_id
    assert (
        resumed_submission.normalization_version == values["normalized_note"].normalization_version
    )
    assert resumed_submission.selected_icd_codes == ["1A00"]
    assert fake_graph.invoke_calls[0]["config"]["configurable"]["thread_id"] == str(thread_id)


def test_post_decision_when_not_pending_returns_409() -> None:
    fake_graph = FakeCompiledGraph(
        snapshot=FakeStateSnapshot(values={"clinical_decision": object()}, interrupts=())
    )
    client = TestClient(make_app(fake_graph))

    response = client.post(
        f"/api/v1/reviews/{uuid4()}/decision",
        json={"selected_icd_codes": ["1A00"]},
    )

    assert response.status_code == 409


def test_post_decision_unknown_thread_returns_404() -> None:
    fake_graph = FakeCompiledGraph(snapshot=FakeStateSnapshot(values={}))
    client = TestClient(make_app(fake_graph))

    response = client.post(
        f"/api/v1/reviews/{uuid4()}/decision",
        json={"selected_icd_codes": ["1A00"]},
    )

    assert response.status_code == 404


def test_post_decision_resume_failure_translated_without_leaking_internals() -> None:
    snapshot, _ = make_pending_snapshot()
    fake_graph = FakeCompiledGraph(
        snapshot=snapshot,
        invoke_error=RuntimeError("redis.exceptions.ConnectionError: refused"),
    )
    client = TestClient(make_app(fake_graph))

    response = client.post(
        f"/api/v1/reviews/{uuid4()}/decision",
        json={"selected_icd_codes": ["1A00"]},
    )

    assert response.status_code == 502
    assert "ConnectionError" not in response.json()["detail"]


def test_router_does_not_call_application_services_directly() -> None:
    """
    Structural guard: the router module must depend only on ``get_graph``
    (plus request/response schemas and the transient
    ``PhysicianDecisionSubmission`` resume-payload constructor) -- never a
    concrete ``ClinicalDecisionService``/``PersistenceService``/
    ``ClinicalReasoningService`` or a repository, all of which stay owned
    by the graph the router only invokes/resumes.
    """
    source = inspect.getsource(review)
    forbidden = [
        "ClinicalDecisionService",
        "PersistenceService",
        "ClinicalReasoningService",
        "Repository",
        "sqlite3",
        "redis",
        "get_container",
    ]
    for symbol in forbidden:
        assert symbol not in source, f"router must not reference {symbol!r} directly"
