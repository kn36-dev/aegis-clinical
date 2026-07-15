"""
cache_lookup node.

Thin LangGraph wrapper around ``CacheService.lookup()``: given the
workflow's ``NormalizedClinicalNote``, checks whether a physician-approved
``ClinicalDecision`` already exists for this semantic observation. A hit
is signalled by populating ``state["clinical_decision"]``; the graph's
conditional edge out of this node (not this node itself) decides whether
execution ends here or continues to retrieval. Contains no cache-key
derivation or lookup logic of its own -- that stays owned by the service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aegis.graphs.state import AegisWorkflowState, WorkflowNode
    from aegis.services.cache_service import CacheService


def make_cache_lookup_node(cache_service: CacheService) -> WorkflowNode:
    """Bind ``cache_service`` into a LangGraph node callable."""

    async def cache_lookup(state: AegisWorkflowState) -> dict[str, Any]:
        decision = cache_service.lookup(state["normalized_note"])
        if decision is None:
            return {}
        return {"clinical_decision": decision}

    return cache_lookup
