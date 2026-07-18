# src/aegis/api/schemas/demo.py
"""
API schema for the demo patient identity listing boundary
(GET /api/v1/demo/patients).
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class DemoPatientResponse(BaseModel):
    """One deterministic demo-profile patient identity, as surfaced to a physician submission UI."""

    patient_id: UUID
    display_name: str
