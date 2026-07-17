"""
generate_recommendation node.

Thin LangGraph wrapper around ``ClinicalReasoningService.reason()``: turns
the workflow's ``ReasoningContext`` into the immutable, advisory
``CodingRecommendation``. Contains no reasoning-provider selection, prompt
construction, or output-validation logic of its own -- that stays owned
by the service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aegis.graphs.state import AegisWorkflowState, WorkflowNode
    from aegis.services.clinical_reasoning_service import ClinicalReasoningService


def make_generate_recommendation_node(
    clinical_reasoning_service: ClinicalReasoningService,
) -> WorkflowNode:
    """Bind ``clinical_reasoning_service`` into a LangGraph node callable."""

    async def generate_recommendation(state: AegisWorkflowState) -> dict[str, Any]:
        coding_recommendation = await clinical_reasoning_service.reason(state["reasoning_context"])
        return {"coding_recommendation": coding_recommendation}

    return generate_recommendation
