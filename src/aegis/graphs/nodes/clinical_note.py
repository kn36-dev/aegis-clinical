"""
create_clinical_note node.

Thin LangGraph wrapper around ``ClinicalNoteService``: turns the
workflow's input ``ClinicalNoteSubmission`` into the immutable
``ClinicalNote`` artifact every downstream node operates on. Contains no
business logic of its own -- construction and persistence stay owned by
the service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aegis.graphs.state import AegisWorkflowState, WorkflowNode
    from aegis.services.clinical_note_service import ClinicalNoteService


def make_create_clinical_note_node(
    clinical_note_service: ClinicalNoteService,
) -> WorkflowNode:
    """Bind ``clinical_note_service`` into a LangGraph node callable."""

    async def create_clinical_note(state: AegisWorkflowState) -> dict[str, Any]:
        clinical_note = clinical_note_service.create_clinical_note(state["submission"])
        return {"clinical_note": clinical_note}

    return create_clinical_note
