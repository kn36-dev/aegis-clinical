# src/aegis/api/routers/clinical.py
"""
Clinical ingestion router: POST /api/v1/clinical-notes[/ingest].

Thin HTTP adapter over the already-compiled AEGIS LangGraph workflow. This
router never imports ``ClinicalNoteService``, ``NormalizationService``,
``RetrievalService``, or ``CacheService`` modules directly, constructs no
repository or infrastructure adapter itself, and performs no ICD
validation, recommendation generation, or persistence SQL -- all of that
stays owned by the application services the graph already composes (see
``aegis.graphs.workflow.build_aegis_graph``). ``submit_clinical_note``'s
only job is translating an HTTP request into workflow input and the
workflow's resulting state back into an HTTP response.

``ingest_clinical_note`` is the one exception with a real dependency on an
application service ahead of the graph: it calls the already-assembled
``AegisContainer``'s ``clinical_note_service``/``content_repository`` --
retrieved via ``get_container``, never constructed here -- to close the
"Live-Credential Content Seeding Gap" documented in
``docs/tradeoffs_and_limitations.md``. See that function's docstring for
why persisting ahead of the graph is necessary and safe.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response

from aegis.api.dependencies import get_container, get_graph, get_identity_context
from aegis.api.schemas.clinical import (
    ApprovedICDCodeResponse,
    ClinicalNoteIngestionRequest,
    ClinicalNoteIngestionResponse,
    ClinicalNoteIngestionWithContentRequest,
    WorkflowStatus,
)
from aegis.api.schemas.errors import ErrorResponse
from aegis.models.workflow_commands import ClinicalNoteSubmission

if TYPE_CHECKING:
    from aegis.api.schemas.identity import RequestIdentityContext
    from aegis.application.container import AegisContainer
    from aegis.infrastructure.sqlite.clinical_note_repository import SQLiteClinicalNoteRepository

router = APIRouter()


async def _invoke_workflow(
    graph: Any,
    submission: ClinicalNoteSubmission,
    case_id: UUID,
    response: Response,
    clinical_note_repository: SQLiteClinicalNoteRepository,
) -> ClinicalNoteIngestionResponse:
    """
    Invoke the AEGIS workflow graph under ``case_id`` and translate its
    terminal state into an HTTP response.

    Shared tail of both ingestion routes below -- everything upstream of
    this (how ``submission``/``case_id`` came to exist) differs; the
    graph invocation and response mapping do not.

    Also projects the outcome onto ``patient_case.status`` (Slice 4's
    review-queue discovery mechanism) via ``clinical_note_repository`` --
    LangGraph's own checkpointed state remains authoritative for what
    this workflow may do next; this write only lets a queue listing find
    candidate cases without deserializing checkpoint history. It uses
    exactly the same branch this function already computes the HTTP
    response from, never a separate decision.
    """
    config = {"configurable": {"thread_id": str(case_id)}}

    try:
        result = await graph.ainvoke({"submission": submission, "case_id": case_id}, config=config)
    except Exception as exc:
        print("WORKFLOW FAILURE:", repr(exc))
        raise HTTPException(
            status_code=502,
            detail="Clinical workflow execution failed.",
        ) from exc

    if "clinical_decision" in result:
        # Workflow completed with clinical_decision available.
        decision = result["clinical_decision"]
        clinical_note_repository.mark_archived(decision.case_id)
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
        clinical_note_repository.mark_pending_review(result["clinical_note"].case_id)
        return ClinicalNoteIngestionResponse(
            workflow_id=case_id,
            case_id=result["clinical_note"].case_id,
            status=WorkflowStatus.PENDING_REVIEW,
        )

    raise HTTPException(
        status_code=502,
        detail="Clinical workflow returned an unrecognized terminal state.",
    )


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
    container: AegisContainer = Depends(get_container),
    identity: RequestIdentityContext = Depends(get_identity_context),
) -> ClinicalNoteIngestionResponse:
    """
    Submit a clinical note into the AEGIS workflow graph.

    Builds a ``ClinicalNoteSubmission`` from the request, generates the
    canonical ``case_id`` for this workflow run, and invokes the graph
    under that id as both the checkpoint ``thread_id`` and
    ``state["case_id"]`` -- see ``_invoke_workflow`` for how the
    resulting terminal state becomes a response. Resuming a pending
    review is out of scope here; see Slice 2.

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
    return await _invoke_workflow(
        graph, submission, case_id, response, container.clinical_note_repository
    )


@router.post(
    "/clinical-notes/ingest",
    response_model=ClinicalNoteIngestionResponse,
    status_code=202,
    responses={
        502: {"model": ErrorResponse, "description": "Clinical workflow execution failed."},
    },
)
async def ingest_clinical_note(
    payload: ClinicalNoteIngestionWithContentRequest,
    response: Response,
    graph: Any = Depends(get_graph),
    container: AegisContainer = Depends(get_container),
    identity: RequestIdentityContext = Depends(get_identity_context),
) -> ClinicalNoteIngestionResponse:
    """
    Ingest raw clinical note content and start the AEGIS workflow in one call.

    Closes the "Live-Credential Content Seeding Gap"
    (``docs/tradeoffs_and_limitations.md``): ``clinical_note_content`` has a
    hard foreign key to ``patient_case``, so content can only be stored once
    a ``patient_case`` row exists for this ``case_id``, and nothing before
    this endpoint could seed that content ahead of the workflow needing it
    during normalization.

    Resolution: mint ``case_id``/``content_reference`` here, call
    ``ClinicalNoteService.create_clinical_note`` directly to establish the
    ``patient_case`` row those content rows foreign-key against, then store
    the raw text through the same ``ClinicalNoteContentRepository``
    abstraction ``NormalizationService`` reads from later. The graph's own
    ``create_clinical_note`` node then re-persists the identical
    ``ClinicalNote`` a moment later when ``_invoke_workflow`` runs it --
    ``SQLiteClinicalNoteRepository.save`` is idempotent for exactly this
    case (unchanged ``case_id``/``patient_id``/``content_reference``), so
    that second persist is a no-op rather than a constraint violation. No
    LangGraph node, normalization/retrieval/reasoning service, or
    ``ClinicalNote`` field changes as part of this -- only the ingress
    boundary and its persistence adapter's idempotency guarantee.
    """
    case_id = uuid4()
    content_reference = str(uuid4())
    submission = ClinicalNoteSubmission(
        patient_id=payload.patient_id,
        content_reference=content_reference,
    )

    container.clinical_note_service.create_clinical_note(submission, case_id=case_id)
    container.content_repository.save_content(case_id, content_reference, payload.note_text)

    return await _invoke_workflow(
        graph, submission, case_id, response, container.clinical_note_repository
    )
