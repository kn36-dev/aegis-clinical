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

Optionally, this router also projects the raw ``RetrievalResult`` /
``ReasoningContext`` / ``CodingRecommendation`` artifact each stage
already carries in that same checkpointed state -- see
``_ARTIFACT_FIELDS``. Nothing is reconstructed or independently
persisted: the artifact is exactly the field the corresponding node
(``aegis.graphs.nodes.retrieval``/``context_assembly``/
``generate_recommendation``) already wrote into ``AegisWorkflowState``,
serialized via that domain model's own ``model_dump(mode="json")``.
Exposure is gated two ways, both of which must hold:

    server:  AppSettings.EXPOSE_WORKFLOW_ARTIFACTS is True
    caller:  ?include_artifacts=true

Either side missing means every stage's ``artifact`` is ``None`` --
this is a PHI/debug boundary (see ``aegis.config.AppSettings``), not a
performance optimization, so it fails closed rather than open.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Depends, HTTPException, Query

from aegis.api.dependencies import get_graph, get_identity_context
from aegis.api.schemas.errors import ErrorResponse
from aegis.api.schemas.identity import RequestIdentityContext  # noqa: TC001
from aegis.api.schemas.review import ReviewWorkflowStatus
from aegis.api.schemas.workflow import (
    WorkflowObservabilityResponse,
    WorkflowStageArtifact,
    WorkflowStageResponse,
)
from aegis.config import get_settings

router = APIRouter()

# Maps a completed node name to the ``AegisWorkflowState`` field it wrote --
# only the three stages this endpoint can expose an artifact for. Every
# other node (create_clinical_note, normalize_note, cache_lookup,
# human_review_pending, decide_case, persist_clinical_decision, cache_store)
# is intentionally absent: this slice only surfaces retrieval candidates,
# the assembled reasoning context, and the AI recommendation output.
_ARTIFACT_FIELDS: dict[str, str] = {
    "retrieve_candidates": "retrieval_result",
    "assemble_context": "reasoning_context",
    "generate_recommendation": "coding_recommendation",
}


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
    include_artifacts: bool = Query(
        default=False,
        description=(
            "Request the raw artifact (RetrievalResult/ReasoningContext/"
            "CodingRecommendation) each stage produced, in addition to its "
            "node name and timestamp. Only honored when the server also "
            "has AppSettings.EXPOSE_WORKFLOW_ARTIFACTS enabled -- otherwise "
            "every stage's artifact is None regardless of this flag."
        ),
    ),
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

    When ``include_artifacts`` and ``AppSettings.EXPOSE_WORKFLOW_ARTIFACTS``
    both hold, the *later* snapshot's own ``values`` -- already being read
    for every other purpose in this loop -- also supplies the artifact a
    ``_ARTIFACT_FIELDS``-listed node just wrote, serialized via that
    domain model's ``model_dump(mode="json")``.
    """
    expose_artifacts = include_artifacts and get_settings().EXPOSE_WORKFLOW_ARTIFACTS

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

        artifact: WorkflowStageArtifact | None = None
        artifact_field = _ARTIFACT_FIELDS.get(node)
        if expose_artifacts and artifact_field is not None and artifact_field in later.values:
            artifact = WorkflowStageArtifact(
                artifact_type=artifact_field,
                payload=later.values[artifact_field].model_dump(mode="json"),
            )

        stages.append(
            WorkflowStageResponse(node=node, completed_at=later.created_at, artifact=artifact)
        )

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
