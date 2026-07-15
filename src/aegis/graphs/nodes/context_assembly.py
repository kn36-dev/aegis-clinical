"""
assemble_context node.

Thin LangGraph wrapper around ``ContextAssembler``: turns the workflow's
``RetrievalResult`` and ``NormalizedClinicalNote`` into the immutable
``ReasoningContext`` that will be handed to clinical reasoning once that
phase exists. Contains no candidate selection or bounding logic of its
own -- that stays owned by the service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aegis.graphs.state import AegisWorkflowState, WorkflowNode
    from aegis.services.context_assembler import ContextAssembler


def make_assemble_context_node(
    context_assembler: ContextAssembler,
) -> WorkflowNode:
    """Bind ``context_assembler`` into a LangGraph node callable."""

    async def assemble_context(state: AegisWorkflowState) -> dict[str, Any]:
        reasoning_context = context_assembler.assemble(
            retrieval_result=state["retrieval_result"],
            normalized_note=state["normalized_note"],
        )
        return {"reasoning_context": reasoning_context}

    return assemble_context
