# src/aegis/api/routers/clinical.py
# Below should be included
# POST /api/v1/clinical/ingest
# GET /api/v1/patients
# GET /api/v1/patients/{patient_id}
# GET /api/v1/patients/{patient_id}/timeline
# And many more in /api_contract_plan.md

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends

from aegis.api.dependencies import get_graph_checkpointer
from aegis.graphs.workflow import compiled_clinical_graph

# 2. HIDE TYPE-ONLY IMPORTS FROM THE RUNTIME ENGINE
if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig

    from aegis.graphs.state import PatientGraphState

router = APIRouter()


@router.post("/ingest")
async def ingest_patient_record(
    payload: dict[str, Any],
    checkpointer: Annotated[Any, Depends(get_graph_checkpointer)],
) -> dict[str, Any]:
    """
    Ingress endpoint receiving raw unstructured clinical data, wrapping it inside
    the system's strict state boundary, and initializing the LangGraph pipeline execution.
    """
    case_id = str(uuid.uuid4())

    # Explicitly type the execution metadata to satisfy LangChain's RunnableConfig type definition
    config: RunnableConfig = {"configurable": {"thread_id": case_id}}

    # Enforce schema validation at the edge before passing raw values into the graph core
    initial_state: PatientGraphState = {
        "case_id": case_id,
        "patient_id": payload.get("patient_id", "p-mock-1"),
        "raw_note": payload.get("note", ""),
        "anonymized_note": "",
        "extracted_codes": [],
        "confidence_score": 0.0,
        "status": "QUEUED",
        "hitl_rejection_notes": "",
    }

    # Executes asynchronously until completion or hitting a manual review gate
    final_state = await compiled_clinical_graph.ainvoke(initial_state, config=config)

    return {"case_id": case_id, "status": final_state["status"]}
