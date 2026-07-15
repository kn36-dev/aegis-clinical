# src/aegis/api/routers/clinical.py
# Below should be included
# POST /api/v1/clinical/ingest
# GET /api/v1/patients
# GET /api/v1/patients/{patient_id}
# GET /api/v1/patients/{patient_id}/timeline
# And many more in /api_contract_plan.md

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter()

_NOT_IMPLEMENTED_DETAIL = (
    "Clinical ingestion is not available yet. The AEGIS workflow graph currently "
    "implements only the deterministic preparation pipeline (normalization, "
    "retrieval, context assembly); ClinicalReasoningService, "
    "ClinicalDecisionService, and PersistenceService are not implemented yet."
)


@router.post("/ingest")
async def ingest_patient_record(payload: dict[str, Any]) -> dict[str, Any]:
    """Ingress endpoint for raw clinical submissions."""
    raise HTTPException(status_code=501, detail=_NOT_IMPLEMENTED_DETAIL)
