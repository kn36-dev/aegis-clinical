"""
persist_clinical_decision node.

Thin LangGraph wrapper around ``PersistenceService.persist()``: durably
commits the workflow's authoritative ``ClinicalDecision`` to
system-of-record storage. The graph -- not this node, and not
``PersistenceService`` or ``CacheService`` -- owns the guarantee that
``cache_store`` only runs once this node has completed without raising;
see its placement ahead of ``cache_store`` in
``aegis.graphs.workflow.build_aegis_graph``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aegis.graphs.state import AegisWorkflowState, WorkflowNode
    from aegis.services.persistence_service import PersistenceService


def make_persist_clinical_decision_node(
    persistence_service: PersistenceService,
) -> WorkflowNode:
    """Bind ``persistence_service`` into a LangGraph node callable."""

    async def persist_clinical_decision(state: AegisWorkflowState) -> dict[str, Any]:
        persistence_service.persist(state["clinical_decision"])
        return {}

    return persist_clinical_decision
