"""
In-memory test doubles for the application composition root tests.

None of these fakes touch SQLite, Redis, Upstash, or an LLM provider --
they exist purely to prove that ``AegisContainer`` and ``build_container``
depend only on the protocol/ABC boundaries the application services
declare, never on a specific infrastructure implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from aegis.models.clinical_decision import ClinicalDecision
from aegis.models.clinical_note import ClinicalNote
from aegis.models.normalized_clinical_note import NormalizedClinicalNote
from aegis.models.reasoning_context import ReasoningContext
from aegis.phi.base import PHIAnonymizer
from aegis.retrieval.providers.base import VectorMatch
from aegis.services.clinical_reasoning_service import ReasoningProvider

FIXED_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)
KNOWN_ICD_CODE = "1A00"


class FakeClinicalNoteRepository:
    """In-memory stand-in for ``ClinicalNoteRepository``."""

    def __init__(self) -> None:
        self.saved: dict[UUID, ClinicalNote] = {}

    def save(self, clinical_note: ClinicalNote) -> None:
        self.saved[clinical_note.case_id] = clinical_note


class FakeContentRepository:
    """In-memory stand-in for ``ClinicalNoteContentRepository``."""

    def __init__(self, content_by_reference: dict[str, str] | None = None) -> None:
        self._content = content_by_reference or {}

    def get_content(self, content_reference: str) -> str:
        return self._content.get(content_reference, "Patient reports no fever. Mild cough.")


class FakePHIAnonymizer(PHIAnonymizer):
    """Identity anonymizer -- avoids loading the real Presidio/spaCy stack in tests."""

    def anonymize(self, text: str) -> str:
        return text


class FakeClinicalDecisionCacheRepository:
    """In-memory stand-in for ``ClinicalDecisionCacheRepository``."""

    def __init__(self) -> None:
        self._store: dict[str, ClinicalDecision] = {}

    def get(self, cache_key: str) -> ClinicalDecision | None:
        return self._store.get(cache_key)

    def set(self, cache_key: str, decision: ClinicalDecision) -> None:
        self._store[cache_key] = decision


class FakeEmbeddingProvider:
    """In-memory stand-in for ``EmbeddingProvider``."""

    def __init__(self, vector: list[float] | None = None) -> None:
        self._vector = vector or [0.1, 0.2, 0.3]

    def embed_query(self, text: str) -> list[float]:
        return self._vector


class FakeVectorQueryProvider:
    """In-memory stand-in for ``VectorQueryProvider``."""

    def __init__(self, matches: list[VectorMatch] | None = None) -> None:
        self._matches = matches if matches is not None else [make_vector_match()]

    def query(self, embedding: list[float], top_k: int) -> list[VectorMatch]:
        return self._matches[:top_k]


def make_vector_match(icd_code: str = KNOWN_ICD_CODE, title: str = "Cholera") -> VectorMatch:
    return VectorMatch(
        id=icd_code,
        score=0.91,
        metadata={
            "code": icd_code,
            "title": title,
            "context_path": "Chapter 1 -> 1A00",
            "embedded_text": f"{title} is an acute condition.",
        },
    )


class FakeReasoningProvider(ReasoningProvider):
    """In-memory stand-in for ``ReasoningProvider``."""

    def __init__(self, icd_code: str = KNOWN_ICD_CODE) -> None:
        self._icd_code = icd_code

    def reason(self, context: ReasoningContext, prompt: str) -> dict[str, Any]:
        return {
            "recommendations": [
                {
                    "icd_code": self._icd_code,
                    "supporting_findings": ["mild cough"],
                    "conflicting_findings": [],
                    "justification": "Consistent with reported findings.",
                    "model_confidence": 0.8,
                }
            ],
            "reasoning_summary": "Findings are consistent with the candidate diagnosis.",
        }


class FakeICDCodeValidator:
    """In-memory stand-in for ``ICDCodeValidator``."""

    def __init__(self, known_codes: set[str] | None = None) -> None:
        self._known_codes = known_codes if known_codes is not None else {KNOWN_ICD_CODE}

    def is_valid(self, icd_code: str) -> bool:
        return icd_code in self._known_codes


class FakeClinicalDecisionRepository:
    """In-memory stand-in for ``ClinicalDecisionRepository``."""

    def __init__(self) -> None:
        self.saved: dict[UUID, ClinicalDecision] = {}

    def save(self, clinical_decision: ClinicalDecision) -> None:
        self.saved[clinical_decision.decision_id] = clinical_decision


def make_normalized_note(clinical_note: ClinicalNote) -> NormalizedClinicalNote:
    return NormalizedClinicalNote(
        clinical_note=clinical_note,
        normalized_text="Patient reports no fever. Mild cough.",
        normalization_version="1.0",
        created_at=FIXED_TIME,
    )


def make_submission_kwargs() -> dict[str, Any]:
    return {
        "patient_id": uuid4(),
        "content_reference": "content-store://clinical-notes/abc123",
    }
