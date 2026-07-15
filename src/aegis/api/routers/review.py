# src/aegis/api/routers/review.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter()

_NOT_IMPLEMENTED_DETAIL = (
    "Physician review approval is not available yet. ClinicalReasoningService "
    "and ClinicalDecisionService are not implemented yet."
)


@router.post("/approve")
async def approve_hitl_case(case_id: str) -> dict[str, str]:
    """Physician review approval endpoint."""
    raise HTTPException(status_code=501, detail=f"Case {case_id}: {_NOT_IMPLEMENTED_DETAIL}")
