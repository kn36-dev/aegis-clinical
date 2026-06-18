# src/aegis/graphs/state.py
from typing import Any, Dict, List, TypedDict


class PatientGraphState(TypedDict):
    case_id: str  # The unique execution Thread ID
    patient_id: str
    raw_note: str  # The original input string from the doctor
    anonymized_note: str  # The text block AFTER scrubbing names
    extracted_codes: List[Dict[str, Any]]  # Array of structured JSON ICD-11 items
    confidence_score: float  # Validation metric evaluated by PydanticAI
    status: str  # PENDING_AI, PENDING_HITL, or ARCHIVED
    hitl_rejection_notes: str
