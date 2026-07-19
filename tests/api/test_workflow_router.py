# tests/api/test_workflow_router.py
"""
Router-level tests for GET /api/v1/workflows/{workflow_id}.

Exercises ``aegis.api.routers.workflow`` against a fake compiled graph
(via ``app.dependency_overrides[get_graph]``) that returns a scripted
``aget_state_history`` sequence -- these tests prove the HTTP adapter's
translation of real LangGraph checkpoint history into stage/timestamp
data, not workflow or service correctness (that's covered by
``tests/graphs/test_workflow_integration.py``). No SQLite, Redis, Upstash
Vector, or LLM is ever touched.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, AsyncIterator
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langgraph.types import Interrupt

from aegis.api.dependencies import get_graph
from aegis.api.routers import workflow

if TYPE_CHECKING:
    import pytest

FIXED_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


@dataclass
class FakeStateSnapshot:
    """Stands in for the fields of LangGraph's ``StateSnapshot`` this router reads."""

    values: dict[str, Any]
    next: tuple[str, ...]
    created_at: datetime
    interrupts: tuple[Interrupt, ...] = ()


@dataclass
class FakeCompiledGraph:
    """Stands in for the real LangGraph ``CompiledStateGraph`` on ``app.state.graph``."""

    history: list[FakeStateSnapshot] = field(default_factory=list)
    history_error: Exception | None = None

    async def aget_state_history(self, config: dict[str, Any]) -> AsyncIterator[FakeStateSnapshot]:
        if self.history_error is not None:
            raise self.history_error
        # LangGraph's own API yields newest-first; this fake matches that.
        for snapshot in reversed(self.history):
            yield snapshot


def make_app(fake_graph: FakeCompiledGraph) -> FastAPI:
    app = FastAPI()
    app.include_router(workflow.router, prefix="/api/v1/workflows")
    app.dependency_overrides[get_graph] = lambda: fake_graph
    return app


def at(seconds: int) -> datetime:
    return FIXED_TIME + timedelta(seconds=seconds)


def make_pending_history(case_id: Any) -> list[FakeStateSnapshot]:
    """Chronologically-ordered history for a workflow suspended pre-resume."""
    return [
        FakeStateSnapshot(values={}, next=("__start__",), created_at=at(0)),
        FakeStateSnapshot(
            values={"submission": object()}, next=("create_clinical_note",), created_at=at(1)
        ),
        FakeStateSnapshot(
            values={"submission": object(), "clinical_note": _clinical_note(case_id)},
            next=("normalize_note",),
            created_at=at(2),
        ),
        FakeStateSnapshot(
            values={
                "submission": object(),
                "clinical_note": _clinical_note(case_id),
                "normalized_note": object(),
            },
            next=("cache_lookup",),
            created_at=at(3),
        ),
        FakeStateSnapshot(
            values={
                "submission": object(),
                "clinical_note": _clinical_note(case_id),
                "normalized_note": object(),
            },
            next=("retrieve_candidates",),
            created_at=at(4),
        ),
        FakeStateSnapshot(
            values={
                "submission": object(),
                "clinical_note": _clinical_note(case_id),
                "normalized_note": object(),
                "retrieval_result": object(),
            },
            next=("assemble_context",),
            created_at=at(5),
        ),
        FakeStateSnapshot(
            values={
                "submission": object(),
                "clinical_note": _clinical_note(case_id),
                "normalized_note": object(),
                "retrieval_result": object(),
                "reasoning_context": object(),
            },
            next=("generate_recommendation",),
            created_at=at(6),
        ),
        FakeStateSnapshot(
            values={
                "submission": object(),
                "clinical_note": _clinical_note(case_id),
                "normalized_note": object(),
                "retrieval_result": object(),
                "reasoning_context": object(),
                "coding_recommendation": object(),
            },
            next=("human_review_pending",),
            created_at=at(7),
            interrupts=(Interrupt(value={}),),
        ),
    ]


class _FakeClinicalNote:
    def __init__(self, case_id: Any) -> None:
        self.case_id = case_id


def _clinical_note(case_id: Any) -> _FakeClinicalNote:
    return _FakeClinicalNote(case_id)


def test_pending_workflow_reports_stages_completed_so_far() -> None:
    case_id = uuid4()
    workflow_id = uuid4()
    fake_graph = FakeCompiledGraph(history=make_pending_history(case_id))
    client = TestClient(make_app(fake_graph))

    response = client.get(f"/api/v1/workflows/{workflow_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["workflow_id"] == str(workflow_id)
    assert body["case_id"] == str(case_id)
    assert body["status"] == "pending_review"
    assert body["current_node"] == "human_review_pending"
    assert [stage["node"] for stage in body["stages"]] == [
        "create_clinical_note",
        "normalize_note",
        "cache_lookup",
        "retrieve_candidates",
        "assemble_context",
        "generate_recommendation",
    ]
    # Real, recorded timestamps -- monotonically increasing, never estimated.
    timestamps = [stage["completed_at"] for stage in body["stages"]]
    assert timestamps == sorted(timestamps)


def test_completed_workflow_includes_post_resume_stages() -> None:
    case_id = uuid4()
    workflow_id = uuid4()
    history = make_pending_history(case_id)

    class _FakeClinicalDecision:
        def __init__(self, case_id: Any) -> None:
            self.case_id = case_id

    resumed_values = {**history[-1].values, "physician_decision_submission": object()}
    history.append(
        FakeStateSnapshot(values=resumed_values, next=("decide_case",), created_at=at(8))
    )
    history.append(
        FakeStateSnapshot(
            values={**resumed_values, "clinical_decision": _FakeClinicalDecision(case_id)},
            next=("persist_clinical_decision",),
            created_at=at(9),
        )
    )
    history.append(
        FakeStateSnapshot(
            values={**resumed_values, "clinical_decision": _FakeClinicalDecision(case_id)},
            next=("cache_store",),
            created_at=at(10),
        )
    )
    history.append(
        FakeStateSnapshot(
            values={**resumed_values, "clinical_decision": _FakeClinicalDecision(case_id)},
            next=(),
            created_at=at(11),
        )
    )
    fake_graph = FakeCompiledGraph(history=history)
    client = TestClient(make_app(fake_graph))

    response = client.get(f"/api/v1/workflows/{workflow_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["current_node"] is None
    assert [stage["node"] for stage in body["stages"]] == [
        "create_clinical_note",
        "normalize_note",
        "cache_lookup",
        "retrieve_candidates",
        "assemble_context",
        "generate_recommendation",
        "human_review_pending",
        "decide_case",
        "persist_clinical_decision",
        "cache_store",
    ]


def test_unknown_workflow_returns_404() -> None:
    fake_graph = FakeCompiledGraph(history=[])
    client = TestClient(make_app(fake_graph))

    response = client.get(f"/api/v1/workflows/{uuid4()}")

    assert response.status_code == 404


def test_state_history_failure_translated_without_leaking_internals() -> None:
    fake_graph = FakeCompiledGraph(
        history_error=RuntimeError("sqlite3.OperationalError: disk I/O error")
    )
    client = TestClient(make_app(fake_graph))

    response = client.get(f"/api/v1/workflows/{uuid4()}")

    assert response.status_code == 502
    assert "disk I/O error" not in response.json()["detail"]


class _FakeSettings:
    """Minimal stand-in for ``AppSettings`` -- only the field this router reads."""

    def __init__(self, expose_workflow_artifacts: bool) -> None:
        self.EXPOSE_WORKFLOW_ARTIFACTS = expose_workflow_artifacts


class _FakeArtifactModel:
    """Stands in for a domain model (``RetrievalResult``, ...) with a real ``model_dump``."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def model_dump(self, mode: str) -> dict[str, Any]:
        assert mode == "json"
        return self._payload


def make_pending_history_with_real_artifacts(case_id: Any) -> list[FakeStateSnapshot]:
    """
    Same shape as ``make_pending_history``, but ``retrieval_result``,
    ``reasoning_context``, and ``coding_recommendation`` are fakes with a
    real ``model_dump`` rather than bare ``object()`` sentinels, so the
    artifact-serialization path can actually run against them.
    """
    history = make_pending_history(case_id)
    artifact_payloads = {
        "retrieval_result": {"candidates": ["fake-retrieval-payload"]},
        "reasoning_context": {"anonymized_clinical_text": "fake-reasoning-payload"},
        "coding_recommendation": {"reasoning_summary": "fake-recommendation-payload"},
    }
    for snapshot in history:
        for field_name, payload in artifact_payloads.items():
            if field_name in snapshot.values:
                snapshot.values[field_name] = _FakeArtifactModel(payload)
    return history


def test_include_artifacts_omitted_when_server_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_id = uuid4()
    workflow_id = uuid4()
    fake_graph = FakeCompiledGraph(history=make_pending_history_with_real_artifacts(case_id))
    app = make_app(fake_graph)
    monkeypatch.setattr(workflow, "get_settings", lambda: _FakeSettings(False))
    client = TestClient(app)

    response = client.get(f"/api/v1/workflows/{workflow_id}?include_artifacts=true")

    assert response.status_code == 200
    assert all(stage["artifact"] is None for stage in response.json()["stages"])


def test_include_artifacts_omitted_when_caller_does_not_request_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_id = uuid4()
    workflow_id = uuid4()
    fake_graph = FakeCompiledGraph(history=make_pending_history_with_real_artifacts(case_id))
    app = make_app(fake_graph)
    monkeypatch.setattr(workflow, "get_settings", lambda: _FakeSettings(True))
    client = TestClient(app)

    response = client.get(f"/api/v1/workflows/{workflow_id}")

    assert response.status_code == 200
    assert all(stage["artifact"] is None for stage in response.json()["stages"])


def test_include_artifacts_populated_when_server_and_caller_both_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_id = uuid4()
    workflow_id = uuid4()
    fake_graph = FakeCompiledGraph(history=make_pending_history_with_real_artifacts(case_id))
    app = make_app(fake_graph)
    monkeypatch.setattr(workflow, "get_settings", lambda: _FakeSettings(True))
    client = TestClient(app)

    response = client.get(f"/api/v1/workflows/{workflow_id}?include_artifacts=true")

    assert response.status_code == 200
    stages = {stage["node"]: stage for stage in response.json()["stages"]}

    assert stages["retrieve_candidates"]["artifact"] == {
        "artifact_type": "retrieval_result",
        "payload": {"candidates": ["fake-retrieval-payload"]},
    }
    assert stages["assemble_context"]["artifact"] == {
        "artifact_type": "reasoning_context",
        "payload": {"anonymized_clinical_text": "fake-reasoning-payload"},
    }
    assert stages["generate_recommendation"]["artifact"] == {
        "artifact_type": "coding_recommendation",
        "payload": {"reasoning_summary": "fake-recommendation-payload"},
    }
    # Stages that never produce one of the three artifacts stay None even
    # when both sides of the opt-in are satisfied.
    assert stages["create_clinical_note"]["artifact"] is None
    assert stages["normalize_note"]["artifact"] is None
    assert stages["cache_lookup"]["artifact"] is None
