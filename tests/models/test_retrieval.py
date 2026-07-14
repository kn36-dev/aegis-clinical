from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegis.models.clinical_note import ClinicalNote
from aegis.models.normalized_clinical_note import NormalizedClinicalNote
from aegis.models.retrieval import RetrievalCandidate, RetrievalRequest, RetrievalResult


@pytest.fixture
def normalized_note() -> NormalizedClinicalNote:
    return NormalizedClinicalNote(
        clinical_note=ClinicalNote(
            case_id=uuid4(),
            patient_id=uuid4(),
            content_reference="content-store://clinical-notes/abc123",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        normalized_text="Patient reports no fever.",
        normalization_version="1.0",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def make_candidate(icd_code: str = "1A00", similarity_score: float = 0.9) -> RetrievalCandidate:
    return RetrievalCandidate(
        icd_code=icd_code,
        title="Cholera",
        hierarchy_context="Chapter 1 → 1A00",
        chapter_number="01",
        semantic_representation="Cholera is an acute diarrheal infection.",
        similarity_score=similarity_score,
    )


class TestRetrievalRequest:
    def test_requires_positive_top_k(self, normalized_note: NormalizedClinicalNote):
        with pytest.raises(ValidationError):
            RetrievalRequest(
                clinical_note=normalized_note.clinical_note,
                normalized_note=normalized_note,
                top_k=0,
            )

    def test_similarity_threshold_is_optional(self, normalized_note: NormalizedClinicalNote):
        request = RetrievalRequest(
            clinical_note=normalized_note.clinical_note,
            normalized_note=normalized_note,
            top_k=5,
        )

        assert request.similarity_threshold is None

    def test_is_immutable(self, normalized_note: NormalizedClinicalNote):
        request = RetrievalRequest(
            clinical_note=normalized_note.clinical_note,
            normalized_note=normalized_note,
            top_k=5,
        )

        with pytest.raises(ValidationError):
            request.top_k = 10


class TestRetrievalCandidate:
    def test_similarity_score_must_be_bounded(self):
        with pytest.raises(ValidationError):
            make_candidate(similarity_score=1.5)


class TestRetrievalResult:
    def test_rejects_duplicate_icd_codes(self, normalized_note: NormalizedClinicalNote):
        with pytest.raises(ValidationError):
            RetrievalResult(
                normalized_note=normalized_note,
                candidates=[make_candidate("1A00"), make_candidate("1A00")],
            )

    def test_accepts_distinct_icd_codes(self, normalized_note: NormalizedClinicalNote):
        result = RetrievalResult(
            normalized_note=normalized_note,
            candidates=[make_candidate("1A00"), make_candidate("1A01")],
        )

        assert len(result.candidates) == 2

    def test_accepts_empty_candidates(self, normalized_note: NormalizedClinicalNote):
        result = RetrievalResult(normalized_note=normalized_note, candidates=[])

        assert result.candidates == []
