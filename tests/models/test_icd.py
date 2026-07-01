import pytest
from pydantic import ValidationError

from aegis.models.icd import ICDConcept


def test_icd_construction():
    concept = ICDConcept(
        code="CA40",
        title="Pneumonia",
    )

    assert concept.code == "CA40"


def test_icd_requires_code():
    with pytest.raises(ValidationError):
        ICDConcept.model_validate(
            {
                "title": "Pneumonia",
            }
        )


def test_icd_round_trip():
    concept = ICDConcept(
        code="CA40",
        title="Pneumonia",
    )

    restored = ICDConcept.model_validate(concept.model_dump())

    assert restored == concept


from aegis.models.icd import (
    TaxonomyCandidate,
)


def test_candidate_construction():
    candidate = TaxonomyCandidate(
        concept=ICDConcept(
            code="CA40",
            title="Pneumonia",
        ),
        similarity_score=0.92,
    )

    assert candidate.similarity_score == 0.92


def test_candidate_rejects_invalid_score():
    with pytest.raises(ValidationError):
        TaxonomyCandidate(
            concept=ICDConcept(
                code="CA40",
                title="Pneumonia",
            ),
            similarity_score=1.5,
        )


def test_candidate_round_trip():
    candidate = TaxonomyCandidate(
        concept=ICDConcept(
            code="CA40",
            title="Pneumonia",
        ),
        similarity_score=0.92,
    )

    restored = TaxonomyCandidate.model_validate(candidate.model_dump())

    assert restored == candidate


from aegis.models.icd import (
    ICDSuggestion,
)


def test_suggestion_construction():
    suggestion = ICDSuggestion(
        concept=ICDConcept(
            code="CA40",
            title="Pneumonia",
        ),
        confidence=0.95,
        explanation="Symptoms strongly match bacterial pneumonia.",
    )

    assert suggestion.confidence == 0.95


def test_suggestion_rejects_invalid_confidence():
    with pytest.raises(ValidationError):
        ICDSuggestion(
            concept=ICDConcept(
                code="CA40",
                title="Pneumonia",
            ),
            confidence=2.0,
            explanation="",
        )


def test_suggestion_round_trip():
    suggestion = ICDSuggestion(
        concept=ICDConcept(
            code="CA40",
            title="Pneumonia",
        ),
        confidence=0.95,
        explanation="Symptoms strongly match bacterial pneumonia.",
    )

    restored = ICDSuggestion.model_validate(suggestion.model_dump())

    assert restored == suggestion
