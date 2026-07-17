# tests/api/test_error_boundary.py
"""
App-level error boundary tests.

``aegis.api.routers.clinical``/``review`` each translate the failures
they anticipate (graph invocation, state retrieval/resume) into a
specific ``HTTPException`` via their own try/except blocks -- covered by
``tests/api/test_clinical_router.py`` and ``tests/api/test_review_router.py``.
This module instead exercises the global handler registered in
``aegis.api.main`` (the last-resort boundary), by triggering exceptions
those routers do *not* already catch -- e.g. workflow state missing a
key a well-behaved graph should always provide -- and asserting the
response still comes back as the same stable ``{"detail": ...}``
contract, never a raw traceback or exception text.

Uses the real ``aegis.api.main.app`` (not a fresh throwaway ``FastAPI()``
instance, unlike the router-level tests) specifically so the registered
global handler is exercised, with ``get_graph`` overridden so no
lifespan-assembled container, graph, SQLite, or Redis is ever touched --
the app's lifespan itself never runs because the client is not used as a
context manager.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from langgraph.types import Interrupt

from aegis.api.dependencies import get_graph
from aegis.api.main import app

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def client() -> Iterator[TestClient]:
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.pop(get_graph, None)


def test_clinical_submission_malformed_interrupt_state_returns_500_without_leaking(
    client: TestClient,
) -> None:
    """
    A workflow result reporting ``__interrupt__`` without the
    ``clinical_note`` key it should always carry is a bug the router's
    own try/except (which only wraps the ``graph.ainvoke`` call itself)
    does not catch -- exactly the gap the global handler exists for.
    """

    class BrokenGraph:
        async def ainvoke(self, state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
            return {"__interrupt__": ("pending",)}

    app.dependency_overrides[get_graph] = lambda: BrokenGraph()

    response = client.post(
        "/api/v1/clinical-notes",
        json={"patient_id": str(uuid4()), "content_reference": "content-store://clinical-notes/x"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "An unexpected error occurred."}
    assert "clinical_note" not in response.text
    assert "KeyError" not in response.text


def test_review_state_malformed_interrupt_state_returns_500_without_leaking(
    client: TestClient,
) -> None:
    """Same gap, on the review boundary: interrupted but missing ``coding_recommendation``."""

    class Snapshot:
        values = {"submission": object()}
        interrupts = (Interrupt(value={}),)

    class BrokenGraph:
        async def aget_state(self, config: dict[str, Any]) -> Snapshot:
            return Snapshot()

    app.dependency_overrides[get_graph] = lambda: BrokenGraph()

    response = client.get(f"/api/v1/reviews/{uuid4()}")

    assert response.status_code == 500
    assert response.json() == {"detail": "An unexpected error occurred."}
    assert "coding_recommendation" not in response.text
    assert "KeyError" not in response.text
