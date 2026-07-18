# src/aegis/api/routers/workflow.py
"""
Workflow observability router: GET /api/v1/workflows/{workflow_id}.

Fulfills the contract documented (but not yet implemented) in
``aegis.api.routers.api_contract_plan.md`` §5. Thin HTTP adapter over
``graph.aget_state_history`` -- LangGraph's own per-thread checkpoint
log -- never a second, independently maintained progress record. Every
completed step of the AEGIS graph (``aegis.graphs.workflow.build_aegis_graph``)
is already checkpointed with its own real timestamp; this router only
walks that existing history and reshapes it into an HTTP response. It
performs no workflow routing, persistence, or reasoning of its own.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Depends, HTTPException

from aegis.api.dependencies import get_graph, get_identity_context
from aegis.api.schemas.errors import ErrorResponse
from aegis.api.schemas.identity import RequestIdentityContext  # noqa: TC001
from aegis.api.schemas.review import ReviewWorkflowStatus
from aegis.api.schemas.workflow import WorkflowObservabilityResponse, WorkflowStageResponse

router = APIRouter()


@router.get(
    "/{workflow_id}",
    response_model=WorkflowObservabilityResponse,
    responses={
        404: {"model": ErrorResponse, "description": "No workflow found for this id."},
        502: {"model": ErrorResponse, "description": "Failed to retrieve workflow state."},
    },
)
async def get_workflow_observability(
    workflow_id: UUID,
    graph: Any = Depends(get_graph),
    identity: RequestIdentityContext = Depends(get_identity_context),
) -> WorkflowObservabilityResponse:
    """
    Retrieve the real, observed execution history of a workflow run.

    Walks ``graph.aget_state_history`` chronologically (the API yields
    newest-first). For each pair of consecutive snapshots, the node that
    just completed is the *previous* snapshot's own ``next`` -- LangGraph
    always names the node about to run on the snapshot immediately
    before it runs, so pairing consecutive snapshots recovers exactly
    which real node produced each later snapshot, timestamped with that
    later snapshot's own ``created_at``. This requires no new
    instrumentation: the checkpointer already records both.
    """
    config = {"configurable": {"thread_id": str(workflow_id)}}

    try:
        history = [snapshot async for snapshot in graph.aget_state_history(config)]
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Failed to retrieve workflow state.",
        ) from exc

    if not history:
        raise HTTPException(
            status_code=404,
            detail=f"No workflow found for id {workflow_id}.",
        )

    chronological = list(reversed(history))
    latest = chronological[-1]

    stages: list[WorkflowStageResponse] = []
    for earlier, later in zip(chronological, chronological[1:], strict=False):
        node = earlier.next[0] if earlier.next else None
        if node is None or node == "__start__":
            continue
        stages.append(WorkflowStageResponse(node=node, completed_at=later.created_at))

    if "clinical_decision" in latest.values:
        status = ReviewWorkflowStatus.COMPLETED
        case_id = latest.values["clinical_decision"].case_id
    elif "clinical_note" in latest.values:
        status = ReviewWorkflowStatus.PENDING_REVIEW
        case_id = latest.values["clinical_note"].case_id
    else:
        raise HTTPException(
            status_code=502,
            detail="Workflow is in an unrecognized state.",
        )

    current_node = latest.next[0] if latest.next else None

    return WorkflowObservabilityResponse(
        workflow_id=workflow_id,
        case_id=case_id,
        status=status,
        current_node=current_node,
        stages=stages,
    )
