# src/aegis/api/schemas/workflow.py
"""
API schemas for workflow observability (GET /api/v1/workflows/{workflow_id}).

These are HTTP boundary DTOs over LangGraph's own checkpointed execution
history (``graph.aget_state_history``) -- never a second, independently
maintained record of workflow progress. See
``aegis.api.routers.workflow.get_workflow_observability`` for how each
``WorkflowStageResponse`` is derived: one entry per real completed
LangGraph superstep, using that checkpoint's own recorded timestamp.
Nothing here is estimated, interpolated, or padded to a fixed set of
stages -- a cache-hit run legitimately produces fewer entries than a
cache-miss run, and that difference is preserved rather than hidden.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from aegis.api.schemas.review import ReviewWorkflowStatus


class WorkflowStageArtifact(BaseModel):
    """
    Raw domain artifact produced by one completed workflow stage.

    ``artifact_type`` names which ``AegisWorkflowState`` field the
    payload came from (``"retrieval_result"``, ``"reasoning_context"``,
    or ``"coding_recommendation"``) -- see
    ``aegis.api.routers.workflow._ARTIFACT_FIELDS``. ``payload`` is that
    domain model's own ``model_dump(mode="json")`` output, rendered
    exactly as the graph produced it: no re-derivation, no curation, no
    typed re-wrapping into a second schema. This is an observability/
    debug trace surface, not a domain API -- the payload shape tracks
    whatever the corresponding domain model (``aegis.models.retrieval
    .RetrievalResult``, ``aegis.models.reasoning_context.ReasoningContext``,
    ``aegis.models.coding_recommendation.CodingRecommendation``) already
    defines, and callers must not assume a fixed structure beyond that.
    """

    artifact_type: str
    payload: dict[str, Any]


class WorkflowStageResponse(BaseModel):
    """
    One real, completed LangGraph node transition.

    ``node`` is the actual node name from ``aegis.graphs.workflow.build_aegis_graph``
    (e.g. ``"normalize_note"``, ``"retrieve_candidates"``,
    ``"human_review_pending"``) -- not a paraphrased or invented label.
    ``completed_at`` is that transition's own checkpoint timestamp, as
    recorded by the checkpointer at the time it actually happened.

    ``artifact`` is present only for the handful of stages that produce
    one of the three artifacts this endpoint can expose (see
    ``WorkflowStageArtifact``), and only when both the server
    (``AppSettings.EXPOSE_WORKFLOW_ARTIFACTS``) and the caller
    (``?include_artifacts=true``) opt in -- see
    ``aegis.api.routers.get_workflow_observability``. It is ``None`` for
    every other stage, and ``None`` for all stages whenever either side
    of that opt-in is missing.
    """

    node: str
    completed_at: datetime
    artifact: WorkflowStageArtifact | None = None


class WorkflowObservabilityResponse(BaseModel):
    """
    Full observed execution history of one workflow run.

    ``current_node`` is the node LangGraph's own state reports as next to
    execute -- present while the workflow is suspended at
    ``human_review_pending`` (or, transiently, mid-run), ``None`` once the
    workflow has reached its terminal state. ``stages`` is ordered
    chronologically and only ever grows as real progress is observed;
    nothing is synthesized for a stage that has not actually completed.
    """

    workflow_id: UUID
    case_id: UUID
    status: ReviewWorkflowStatus
    current_node: str | None
    stages: list[WorkflowStageResponse]
