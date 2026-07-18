# src/aegis/api/routers/demo.py
"""
Demo patient identity router: GET /api/v1/demo/patients.

Not a patient directory or a CRUD patient API -- there is no create,
update, delete, pagination, search, or sort here, and this deliberately
does not implement the "Patient Workspace" section of
``aegis.api.routers.api_contract_plan``. Its only job is letting a
physician submission UI enumerate the fixed, deterministic patient
identities ``aegis.api.bootstrap.seed_demo_patient_identities`` seeds
into ``patient_identity_vault`` for ``AEGIS_PROFILE == "demo"`` -- the
same real system-of-record table and column set every other patient
identity lives in, not a separate store.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from aegis.api.bootstrap import DEMO_PATIENT_IDENTITIES
from aegis.api.schemas.demo import DemoPatientResponse
from aegis.config import get_settings

router = APIRouter()


@router.get("/patients", response_model=list[DemoPatientResponse])
def list_demo_patients() -> list[DemoPatientResponse]:
    """
    List the fixed demo patient identities available in this environment.

    Returns an empty list -- not a 404 -- whenever ``AEGIS_PROFILE !=
    "demo"``: this route is a permanent part of the API contract, only
    its dataset is profile-scoped. A caller (the physician submission
    UI) always gets a list back and decides how to render zero results;
    it never needs to special-case "this endpoint doesn't exist here".
    """
    settings = get_settings()
    if settings.AEGIS_PROFILE != "demo":
        return []

    return [
        DemoPatientResponse(
            patient_id=UUID(identity.patient_id),
            display_name=(
                f"{identity.first_name} {identity.last_name} ({identity.medical_record_number})"
            ),
        )
        for identity in DEMO_PATIENT_IDENTITIES
    ]
