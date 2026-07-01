# src/aegis/models/symptom.py
# Symptom
# Duration
# Severity
# Negation
# SymptomExtraction

# SymptomExtraction

# Owns

# symptoms
# duration
# severity
# negations


from __future__ import annotations

from enum import Enum

from aegis.models.base import DomainModel


class Severity(str, Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    UNKNOWN = "unknown"


class Symptom(DomainModel):
    """
    One structured clinical finding extracted from a note.
    """

    name: str

    present: bool

    severity: Severity = Severity.UNKNOWN

    duration: str | None = None


class SymptomExtraction(DomainModel):
    """
    Structured findings extracted from one clinical note.
    """

    symptoms: tuple[Symptom, ...]
