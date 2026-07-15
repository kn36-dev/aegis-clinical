"""
normalize_note node.

Thin LangGraph wrapper around ``NormalizationService``: turns the
workflow's ``ClinicalNote`` into the immutable ``NormalizedClinicalNote``
artifact. Contains no normalization or PHI-anonymization logic of its
own -- that stays owned by the service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aegis.graphs.state import AegisWorkflowState, WorkflowNode
    from aegis.services.normalization_service import NormalizationService


def make_normalize_note_node(
    normalization_service: NormalizationService,
) -> WorkflowNode:
    """Bind ``normalization_service`` into a LangGraph node callable."""

    async def normalize_note(state: AegisWorkflowState) -> dict[str, Any]:
        normalized_note = normalization_service.normalize(state["clinical_note"])
        return {"normalized_note": normalized_note}

    return normalize_note
