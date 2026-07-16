# tests/api/test_identity_context.py
"""
Tests for the Slice 4 identity boundary: ``RequestIdentityContext`` and
the ``get_identity_context`` FastAPI dependency.

Proves only that the boundary resolves, that endpoints can accept it
without any change in business behavior, and that the "no authentication
mechanism yet" case is handled by returning an unestablished context --
never by fabricating a default actor. No authentication library, token,
or external identity provider is ever involved.
"""

from __future__ import annotations

import inspect
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from aegis.api import dependencies
from aegis.api.dependencies import get_graph, get_identity_context
from aegis.api.routers import clinical, review
from aegis.api.schemas.identity import RequestIdentityContext
from aegis.models.clinical_decision import (
    ApprovedICDClassification,
    ClinicalDecision,
    RecommendationDisposition,
)

FIXED_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


class FakeCompiledGraph:
    """Stands in for the real LangGraph ``CompiledStateGraph`` on ``app.state.graph``."""

    def __init__(self, result: dict[str, Any]) -> None:
        self._result = result
        self.calls: list[dict[str, Any]] = []

    async def ainvoke(self, state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"state": state, "config": config})
        return self._result

    async def aget_state(self, config: dict[str, Any]) -> Any:
        raise AssertionError("not used by this test module")


def make_decision() -> ClinicalDecision:
    return ClinicalDecision(
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


def test_identity_context_resolves_to_unestablished_context_with_no_auth_adapter() -> None:
    """
    With no future authentication adapter wired in (the current state of
    the codebase), the dependency must not raise, must not read any
    request data, and must not invent a default actor -- it resolves to
    an all-``None`` context.
    """
    test_app = FastAPI()

    @test_app.get("/probe")
    def probe(identity: RequestIdentityContext = Depends(get_identity_context)) -> dict[str, Any]:
        return identity.model_dump()

    with TestClient(test_app) as client:
        response = client.get("/probe")

    assert response.status_code == 200
    assert response.json() == {
        "actor_id": None,
        "actor_type": None,
        "institution_reference": None,
    }


def test_identity_context_relays_whatever_a_future_auth_adapter_attaches() -> None:
    """
    Simulates the extension point a future authentication adapter would
    use: attaching a populated ``RequestIdentityContext`` to
    ``request.state`` upstream of routing (e.g. via middleware).
    ``get_identity_context`` must relay it unchanged rather than
    overriding it with the unestablished default.
    """
    test_app = FastAPI()
    populated = RequestIdentityContext(
        actor_id="physician-123", actor_type="physician", institution_reference="hospital-a"
    )

    @test_app.middleware("http")
    async def attach_identity(request: Any, call_next: Any) -> Any:
        request.state.identity_context = populated
        return await call_next(request)

    @test_app.get("/probe")
    def probe(identity: RequestIdentityContext = Depends(get_identity_context)) -> dict[str, Any]:
        return identity.model_dump()

    with TestClient(test_app) as client:
        response = client.get("/probe")

    assert response.status_code == 200
    assert response.json() == populated.model_dump()


def test_clinical_submission_endpoint_accepts_identity_without_changing_business_behavior() -> None:
    """
    The endpoint's response must be identical regardless of whether
    identity resolves to the unestablished default or a populated
    context -- accepting the dependency must not alter ingestion
    behavior (no authorization gate exists in this slice).
    """
    decision = make_decision()

    def make_app() -> FastAPI:
        app = FastAPI()
        app.include_router(clinical.router, prefix="/api/v1")
        app.dependency_overrides[get_graph] = lambda: FakeCompiledGraph(
            {"clinical_decision": decision}
        )
        return app

    payload = {
        "patient_id": str(uuid4()),
        "content_reference": "content-store://clinical-notes/abc123",
    }

    default_app = make_app()
    with TestClient(default_app) as client:
        default_response = client.post("/api/v1/clinical-notes", json=payload)

    populated_app = make_app()
    populated_app.dependency_overrides[get_identity_context] = lambda: RequestIdentityContext(
        actor_id="physician-123", actor_type="physician"
    )
    with TestClient(populated_app) as client:
        populated_response = client.post("/api/v1/clinical-notes", json=payload)

    assert default_response.status_code == populated_response.status_code == 201
    assert default_response.json() == populated_response.json()


def test_routers_do_not_read_request_headers_or_metadata_directly_for_identity() -> None:
    """
    Structural guard: identity must only ever be resolved through
    ``get_identity_context`` -- routers must not import ``Request``,
    read ``.headers``, or otherwise reach into request metadata to
    derive identity themselves.
    """
    for module in (clinical, review):
        source = inspect.getsource(module)
        assert "Request" not in source, f"{module.__name__} must not depend on Request directly"
        assert ".headers" not in source, f"{module.__name__} must not read headers directly"
        assert "get_identity_context" in source, (
            f"{module.__name__} must depend on the identity boundary"
        )


def test_get_identity_context_does_not_read_request_headers_itself() -> None:
    """
    Structural guard on the adapter itself: the one place identity
    *could* legitimately read request data today has no header/cookie/
    token parsing -- it only relays ``request.state``.
    """
    source = inspect.getsource(dependencies.get_identity_context)
    for forbidden in ("headers", "cookies", "Authorization", "Bearer"):
        assert forbidden not in source, f"get_identity_context must not reference {forbidden!r}"
