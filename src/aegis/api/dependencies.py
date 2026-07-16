# src/aegis/api/dependencies.py
"""
FastAPI dependency providers.

Routers retrieve the single, already-assembled ``AegisContainer`` and
compiled LangGraph graph from ``app.state`` (populated once at startup
by ``api/main.py``'s lifespan via ``aegis.api.bootstrap``) rather than
constructing services, repositories, or infrastructure themselves.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import Request

from aegis.api.schemas.identity import RequestIdentityContext

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

    from aegis.application.container import AegisContainer
    from aegis.graphs.state import AegisWorkflowState


def get_container(request: Request) -> AegisContainer:
    """Retrieve the application-wide ``AegisContainer`` assembled at startup."""
    return request.app.state.container  # type: ignore[no-any-return]


def get_graph(
    request: Request,
) -> CompiledStateGraph[AegisWorkflowState, Any, AegisWorkflowState, AegisWorkflowState]:
    """Retrieve the compiled AEGIS LangGraph workflow assembled at startup."""
    return request.app.state.graph  # type: ignore[no-any-return]


def get_identity_context(request: Request) -> RequestIdentityContext:
    """
    Resolve the caller identity for this request.

    No authentication mechanism exists yet in AEGIS. This provider
    never reads headers, cookies, tokens, or any other request
    metadata itself, and never fabricates a default actor -- it only
    relays whatever a future authentication adapter (e.g. middleware
    sitting in front of routing) has already attached to
    ``request.state.identity_context``. Until that adapter exists,
    every request resolves to a context whose fields are all ``None``,
    which routers and application services must read as "identity not
    yet established," not as an authorization decision.
    """
    return getattr(request.state, "identity_context", None) or RequestIdentityContext()
