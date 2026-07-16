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
