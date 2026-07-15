"""
retrieve_candidates node.

Thin LangGraph wrapper around ``RetrievalService``: turns the workflow's
``NormalizedClinicalNote`` into the immutable ``RetrievalResult``
evidence set.

``top_k`` and ``similarity_threshold`` are deterministic workflow
policy -- how much evidence this graph asks for -- rather than a
``RetrievalService`` concern, so they are configured at the
orchestration boundary and injected here instead of being hardcoded
inside the service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aegis.models.retrieval import RetrievalRequest

if TYPE_CHECKING:
    from aegis.graphs.state import AegisWorkflowState, WorkflowNode
    from aegis.services.retrieval_service import RetrievalService


def make_retrieve_candidates_node(
    retrieval_service: RetrievalService,
    *,
    top_k: int,
    similarity_threshold: float | None = None,
) -> WorkflowNode:
    """Bind ``retrieval_service`` and its policy into a LangGraph node callable."""

    async def retrieve_candidates(state: AegisWorkflowState) -> dict[str, Any]:
        request = RetrievalRequest(
            clinical_note=state["clinical_note"],
            normalized_note=state["normalized_note"],
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )
        retrieval_result = retrieval_service.retrieve(request)
        return {"retrieval_result": retrieval_result}

    return retrieve_candidates
