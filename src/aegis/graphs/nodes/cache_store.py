"""
cache_store node.

Thin LangGraph wrapper around ``CacheService.store()``: records the
just-persisted ``ClinicalDecision`` for future deterministic reuse.
``CacheService`` itself has no opinion on when storage should occur
(see ``cache_service.py``'s module docstring) -- the graph owns that
ordering by placing this node after ``persist_clinical_decision``, so
storage is only ever reached once durable persistence has succeeded.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aegis.graphs.state import AegisWorkflowState, WorkflowNode
    from aegis.services.cache_service import CacheService


def make_cache_store_node(cache_service: CacheService) -> WorkflowNode:
    """Bind ``cache_service`` into a LangGraph node callable."""

    async def cache_store(state: AegisWorkflowState) -> dict[str, Any]:
        cache_service.store(state["normalized_note"], state["clinical_decision"])
        return {}

    return cache_store
