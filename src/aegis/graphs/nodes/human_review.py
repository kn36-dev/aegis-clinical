"""
human_review_pending node.

Explicit interrupt/resume boundary between the advisory
``CodingRecommendation`` produced by ``ClinicalReasoningService`` and the
physician-authority boundary owned by ``ClinicalDecisionService``. This
node performs no review logic itself -- it has no injected service
collaborator, unlike every other node in this package.

**This is a workflow suspension boundary, not a decision boundary.** It
does not approve, reject, or modify ``coding_recommendation`` in any
way -- it has no opinion on the recommendation's content and cannot
accept or reject ICD codes. Its entire responsibility is to pause graph
execution and wait. Approval/rejection/modification classification
remains exclusively owned by ``ClinicalDecisionService`` (the
``decide_case`` node downstream), per the physician-authority boundary
described in
``application_service_contracts/clinical_decision_service.md``.

It suspends graph execution via LangGraph's own ``interrupt`` primitive
and surfaces the pending ``CodingRecommendation``, then blocks until an
external caller resumes the graph with ``Command(resume=submission)``,
where ``submission`` is a ``PhysicianDecisionSubmission`` (see
``aegis.services.clinical_decision_service``). This invents no approval
API of its own -- physician UI and review endpoints remain out of scope
(see CLAUDE.md's Development status) -- it only wires the graph-native
resumability primitive so that boundary can be built later without
reshaping this graph.

**``PhysicianDecisionSubmission`` is a transient resume payload, not an
authoritative domain artifact.** It exists only to cross the
interrupt/resume boundary and hand physician input to ``decide_case``
in the same graph run; it is not a ``runtime_domain_contracts`` model,
carries no institutional authority of its own, and must never be
treated as, or persisted in place of, the ``ClinicalDecision`` that
``ClinicalDecisionService`` alone produces. Concretely: it is not
written by ``PersistenceService``, is not stored by ``CacheService``,
and has no repository of its own -- once ``decide_case`` consumes it to
construct a ``ClinicalDecision``, its purpose is served and it should
not be propagated, replayed, or treated as durable workflow history.
Its presence in ``AegisWorkflowState`` is graph-checkpoint bookkeeping
only, not system-of-record truth.

Requires a checkpointer on the compiled graph; see
``aegis.graphs.workflow.build_aegis_graph``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langgraph.types import interrupt

if TYPE_CHECKING:
    from aegis.graphs.state import AegisWorkflowState


async def human_review_pending(state: AegisWorkflowState) -> dict[str, Any]:
    """
    Suspend the graph pending physician review; approve/reject nothing.

    ``interrupt`` halts execution here and re-raises on every resumed
    re-execution of this node until a caller supplies a resume value,
    which this function then merely relays into state under
    ``physician_decision_submission`` for ``decide_case`` to consume --
    it is not inspected, validated, or acted on here.
    """
    physician_decision_submission = interrupt(
        {"coding_recommendation": state["coding_recommendation"]}
    )
    return {"physician_decision_submission": physician_decision_submission}
