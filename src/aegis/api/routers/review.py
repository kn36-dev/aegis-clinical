# src/aegis/api/routers/review.py
"""
Physician review router:
GET /api/v1/reviews/{thread_id} and POST /api/v1/reviews/{thread_id}/decision.

Thin HTTP adapter over the already-compiled AEGIS LangGraph workflow's
``human_review_pending`` interrupt/resume boundary (see
``aegis.graphs.nodes.human_review``). This router does not call
``ClinicalDecisionService`` or ``PersistenceService`` directly, perform ICD
validation, or decide ACCEPTED/ADDED/REMOVED/MODIFIED disposition -- all of
that stays owned by the graph's ``decide_case`` and
``persist_clinical_decision`` nodes once resumed. Its only job is
translating an HTTP request into ``graph.aget_state``/
``graph.ainvoke(Command(resume=...))`` calls and the resulting workflow
state back into an HTTP response.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Depends, HTTPException
from langgraph.types import Command

from aegis.api.dependencies import get_graph, get_identity_context
from aegis.api.schemas.errors import ErrorResponse
from aegis.api.schemas.identity import RequestIdentityContext  # noqa: TC001
from aegis.api.schemas.review import (
    ApprovedICDCodeResponse,
    PhysicianDecisionSubmissionRequest,
    RecommendedICDCodeResponse,
    ReviewDecisionResponse,
    ReviewStateResponse,
    ReviewWorkflowStatus,
)
from aegis.models.workflow_commands import PhysicianDecisionSubmission

router = APIRouter()


def _thread_config(thread_id: UUID) -> dict[str, Any]:
    """
    Build the LangGraph ``configurable.thread_id`` for a review's workflow.

    ``thread_id`` here is exactly ``case_id`` -- the canonical workflow
    identity ``POST /api/v1/clinical-notes`` generates ahead of graph
    invocation and ``ClinicalNoteService`` assigns to the resulting
    ``ClinicalNote`` (see ``aegis.api.routers.clinical``). It is also
    what ``patient_case.thread_id`` persists (``str(case_id)``, see
    ``SQLiteClinicalNoteRepository``). This router treats it as-is
    rather than introducing a separate review identity, so the same
    value identifies the case everywhere: persisted state, the LangGraph
    checkpoint, and this review resume boundary.
    """
    return {"configurable": {"thread_id": str(thread_id)}}


@router.get(
    "/{thread_id}",
    response_model=ReviewStateResponse,
    responses={
        404: {"model": ErrorResponse, "description": "No workflow found for this thread id."},
        502: {"model": ErrorResponse, "description": "Failed to retrieve workflow state."},
    },
)
async def get_review_state(
    thread_id: UUID,
    graph: Any = Depends(get_graph),
    identity: RequestIdentityContext = Depends(get_identity_context),
) -> ReviewStateResponse:
    """
    Retrieve the current pending or completed review state for a workflow.

    Reads the workflow's own checkpointed state via ``graph.aget_state``
    rather than reproducing any state-transition logic here: an empty
    snapshot means no workflow was ever run under this thread id, a
    pending interrupt means it is suspended at ``human_review_pending``,
    and a ``clinical_decision`` in the snapshot means review already
    completed.

    ``identity`` is the Slice 4 identity boundary (see
    ``aegis.api.schemas.identity``) -- resolved via
    ``get_identity_context``, not read from headers here, and not yet
    used to gate access to this state. That is an authorization
    decision, deliberately out of scope for this slice.
    """
    try:
        snapshot = await graph.aget_state(_thread_config(thread_id))
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Failed to retrieve workflow state.",
        ) from exc

    if not snapshot.values:
        raise HTTPException(
            status_code=404,
            detail=f"No workflow found for thread {thread_id}.",
        )

    if "clinical_decision" in snapshot.values:
        decision = snapshot.values["clinical_decision"]
        return ReviewStateResponse(
            workflow_id=thread_id,
            case_id=decision.case_id,
            status=ReviewWorkflowStatus.COMPLETED,
            decision_id=decision.decision_id,
            approved_icd_codes=[
                ApprovedICDCodeResponse(
                    icd_code=classification.icd_code,
                    disposition=classification.disposition.value,
                )
                for classification in decision.approved_icd_codes
            ],
        )

    if snapshot.interrupts:
        coding_recommendation = snapshot.values["coding_recommendation"]
        normalized_note = snapshot.values["normalized_note"]
        return ReviewStateResponse(
            workflow_id=thread_id,
            case_id=coding_recommendation.case_id,
            status=ReviewWorkflowStatus.PENDING_REVIEW,
            recommendation_id=coding_recommendation.recommendation_id,
            reasoning_summary=coding_recommendation.reasoning_summary,
            normalized_note_text=normalized_note.normalized_text,
            recommended_icd_codes=[
                RecommendedICDCodeResponse(
                    icd_code=recommendation.icd_code,
                    justification=recommendation.justification,
                    model_confidence=recommendation.model_confidence,
                    supporting_findings=recommendation.supporting_findings,
                    conflicting_findings=recommendation.conflicting_findings,
                )
                for recommendation in coding_recommendation.recommendations
            ],
        )

    raise HTTPException(
        status_code=502,
        detail="Workflow is in an unrecognized state.",
    )


@router.post(
    "/{thread_id}/decision",
    response_model=ReviewDecisionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "No workflow found for this thread id."},
        409: {
            "model": ErrorResponse,
            "description": "Workflow is not currently awaiting physician review.",
        },
        502: {"model": ErrorResponse, "description": "Clinical workflow resume failed."},
    },
)
async def submit_review_decision(
    thread_id: UUID,
    payload: PhysicianDecisionSubmissionRequest,
    graph: Any = Depends(get_graph),
    identity: RequestIdentityContext = Depends(get_identity_context),
) -> ReviewDecisionResponse:
    """
    Submit a physician's review decision and resume the suspended workflow.

    Reads case/recommendation/patient/normalization identity out of the
    workflow's own suspended state (never trusts it from the request),
    combines it with the physician-submitted ICD codes into a
    ``PhysicianDecisionSubmission``, and hands it to the graph via
    ``Command(resume=...)``. Whether each code is accepted, added,
    removed, or modified is decided entirely by ``ClinicalDecisionService``
    once the graph resumes; this router does not construct a
    ``ClinicalDecision`` or call any application service itself.

    ``identity`` is the Slice 4 identity boundary (see
    ``aegis.api.schemas.identity``): resolved via
    ``get_identity_context`` rather than read from headers here. This is
    the endpoint where future physician-attribution audit metadata would
    attach, but neither ``PhysicianDecisionSubmission`` nor
    ``ClinicalDecision`` defines an actor field today, so ``identity`` is
    not threaded any further and this endpoint's business behavior is
    unchanged.
    """
    config = _thread_config(thread_id)

    try:
        snapshot = await graph.aget_state(config)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Failed to retrieve workflow state.",
        ) from exc

    if not snapshot.values:
        raise HTTPException(
            status_code=404,
            detail=f"No workflow found for thread {thread_id}.",
        )

    if not snapshot.interrupts:
        raise HTTPException(
            status_code=409,
            detail="Workflow is not currently awaiting physician review.",
        )

    coding_recommendation = snapshot.values["coding_recommendation"]
    submission = snapshot.values["submission"]
    normalized_note = snapshot.values["normalized_note"]

    physician_decision_submission = PhysicianDecisionSubmission(
        case_id=coding_recommendation.case_id,
        recommendation_id=coding_recommendation.recommendation_id,
        patient_id_reference=submission.patient_id,
        normalization_version=normalized_note.normalization_version,
        selected_icd_codes=payload.selected_icd_codes,
    )

    try:
        result = await graph.ainvoke(Command(resume=physician_decision_submission), config=config)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Clinical workflow resume failed.",
        ) from exc

    if "clinical_decision" not in result:
        raise HTTPException(
            status_code=502,
            detail="Clinical workflow returned an unrecognized terminal state.",
        )

    decision = result["clinical_decision"]
    return ReviewDecisionResponse(
        workflow_id=thread_id,
        case_id=decision.case_id,
        decision_id=decision.decision_id,
        approved_icd_codes=[
            ApprovedICDCodeResponse(
                icd_code=classification.icd_code,
                disposition=classification.disposition.value,
            )
            for classification in decision.approved_icd_codes
        ],
    )
