# PydanticAI forces unstructured agent text
# into structural JSON matching types

# src/aegis/schemas/validation.py
from typing import List

from pydantic import BaseModel, Field


class ICD11Match(BaseModel):
    code: str = Field(..., description="The official WHO ICD-11 identifier (e.g., '1A00').")
    clinical_term: str = Field(..., description="The matching text found in the patient note.")
    confidence: float = Field(..., description="Calculated extraction metric between 0.0 and 1.0.")


class ClinicalExtractionResult(BaseModel):
    matches: List[ICD11Match]
    requires_human_signoff: bool
