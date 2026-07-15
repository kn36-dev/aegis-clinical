"""
decide_case node.

Thin LangGraph wrapper around ``ClinicalDecisionService.decide()``: turns
the workflow's advisory ``CodingRecommendation`` and the
``PhysicianDecisionSubmission`` obtained by resuming
``human_review_pending`` into the immutable, authoritative
``ClinicalDecision``. Contains no approval-classification logic of its
own -- that stays owned by the service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aegis.graphs.state import AegisWorkflowState, WorkflowNode
    from aegis.services.clinical_decision_service import ClinicalDecisionService


def make_decide_case_node(
    clinical_decision_service: ClinicalDecisionService,
) -> WorkflowNode:
    """Bind ``clinical_decision_service`` into a LangGraph node callable."""

    async def decide_case(state: AegisWorkflowState) -> dict[str, Any]:
        clinical_decision = clinical_decision_service.decide(
            recommendation=state["coding_recommendation"],
            submission=state["physician_decision_submission"],
        )
        return {"clinical_decision": clinical_decision}

    return decide_case
