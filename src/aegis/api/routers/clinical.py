# src/aegis/api/routers/clinical.py
"""
Clinical ingestion router: POST /api/v1/clinical-notes.

Thin HTTP adapter over the already-compiled AEGIS LangGraph workflow.
This router does not call ``ClinicalNoteService``, ``NormalizationService``,
``RetrievalService``, ``CacheService``, or any repository directly, and
performs no ICD validation, recommendation generation, or persistence --
all of that stays owned by the application services the graph already
composes (see ``aegis.graphs.workflow.build_aegis_graph``). Its only job
is translating an HTTP request into workflow input and the workflow's
resulting state back into an HTTP response.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response

from aegis.api.dependencies import get_graph, get_identity_context
from aegis.api.schemas.clinical import (
    ApprovedICDCodeResponse,
    ClinicalNoteIngestionRequest,
    ClinicalNoteIngestionResponse,
    WorkflowStatus,
)
from aegis.api.schemas.errors import ErrorResponse
from aegis.models.workflow_commands import ClinicalNoteSubmission

if TYPE_CHECKING:
    from aegis.api.schemas.identity import RequestIdentityContext

router = APIRouter()


@router.post(
    "/clinical-notes",
    response_model=ClinicalNoteIngestionResponse,
    status_code=202,
    responses={
        502: {"model": ErrorResponse, "description": "Clinical workflow execution failed."},
    },
)
async def submit_clinical_note(
    payload: ClinicalNoteIngestionRequest,
    response: Response,
    graph: Any = Depends(get_graph),
    identity: RequestIdentityContext = Depends(get_identity_context),
) -> ClinicalNoteIngestionResponse:
    """
    Submit a clinical note into the AEGIS workflow graph.

    Builds a ``ClinicalNoteSubmission`` from the request, generates the
    canonical ``case_id`` for this workflow run, invokes the graph
    retrieved from application state under that id as both the
    checkpoint ``thread_id`` and ``state["case_id"]``, and maps the
    resulting terminal state -- either a workflow that completed with a
    ``ClinicalDecision`` already available, or one suspended at the
    ``human_review_pending`` interrupt -- into a response. This router
    only detects which of the two the graph reports; the reason (cache
    hit, or any other internal workflow decision) is the graph/services'
    concern, not this adapter's. Resuming a pending review is out of
    scope here; see Slice 2.

    ``identity`` here is the Slice 4 *caller* identity boundary --
    distinct from ``case_id``, the workflow/case identity above. It is
    resolved through ``get_identity_context`` rather than read from
    headers here, and is not yet threaded into ``ClinicalNoteSubmission``
    -- that model defines no actor field today (see
    ``aegis.api.schemas.identity``) -- so accepting it does not change
    this endpoint's business behavior. It exists so a future
    authorization/audit layer has a place to attach.
    """
    submission = ClinicalNoteSubmission(
        patient_id=payload.patient_id,
        content_reference=payload.content_reference,
    )
    # case_id is the canonical workflow identity (see
    # runtime_domain_contracts/clinical_note.md, "Created by: Application
    # ingress after request validation"). It must be generated here,
    # ahead of graph invocation, because LangGraph's checkpoint
    # ``thread_id`` has to be fixed in ``config`` before ``ainvoke`` runs
    # -- before ``create_clinical_note`` (the first node) has a chance to
    # assign identity itself. Passing it through as ``state["case_id"]``
    # makes ``ClinicalNoteService`` assign this exact value to the
    # resulting ``ClinicalNote`` instead of minting an unrelated one, so
    # ``patient_case.thread_id``, the LangGraph checkpoint thread id, and
    # this case's identity are always the same value end to end.
    case_id = uuid4()
    config = {"configurable": {"thread_id": str(case_id)}}

    try:
        result = await graph.ainvoke({"submission": submission, "case_id": case_id}, config=config)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Clinical workflow execution failed.",
        ) from exc

    if "clinical_decision" in result:
        # Workflow completed with clinical_decision available.
        decision = result["clinical_decision"]
        response.status_code = 201
        return ClinicalNoteIngestionResponse(
            workflow_id=case_id,
            case_id=decision.case_id,
            status=WorkflowStatus.COMPLETED,
            decision_id=decision.decision_id,
            approved_icd_codes=[
                ApprovedICDCodeResponse(
                    icd_code=classification.icd_code,
                    disposition=classification.disposition.value,
                )
                for classification in decision.approved_icd_codes
            ],
        )

    if "__interrupt__" in result:
        return ClinicalNoteIngestionResponse(
            workflow_id=case_id,
            case_id=result["clinical_note"].case_id,
            status=WorkflowStatus.PENDING_REVIEW,
        )

    raise HTTPException(
        status_code=502,
        detail="Clinical workflow returned an unrecognized terminal state.",
    )
