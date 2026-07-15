"""
human_review_pending node.

Explicit interrupt/resume boundary between the advisory
``CodingRecommendation`` produced by ``ClinicalReasoningService`` and the
physician-authority boundary owned by ``ClinicalDecisionService``. This
node performs no review logic itself -- it has no injected service
collaborator, unlike every other node in this package.

It suspends graph execution via LangGraph's own ``interrupt`` primitive
and surfaces the pending ``CodingRecommendation``, then blocks until an
external caller resumes the graph with ``Command(resume=submission)``,
where ``submission`` is a ``PhysicianDecisionSubmission`` (see
``aegis.services.clinical_decision_service``). This invents no approval
API of its own -- physician UI and review endpoints remain out of scope
(see CLAUDE.md's Development status) -- it only wires the graph-native
resumability primitive so that boundary can be built later without
reshaping this graph.

Requires a checkpointer on the compiled graph; see
``aegis.graphs.workflow.build_aegis_graph``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langgraph.types import interrupt

if TYPE_CHECKING:
    from aegis.graphs.state import AegisWorkflowState


async def human_review_pending(state: AegisWorkflowState) -> dict[str, Any]:
    physician_decision_submission = interrupt(
        {"coding_recommendation": state["coding_recommendation"]}
    )
    return {"physician_decision_submission": physician_decision_submission}
