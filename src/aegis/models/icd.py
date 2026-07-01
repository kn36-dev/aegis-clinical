# src/aegis/models/icd.py
# ICDSuggestion

# Owns

# code
# title
# confidence
# explanation


# ICDConcept
# TaxonomyCandidate
# ICDSuggestion

from pydantic import Field

from aegis.models.base import DomainModel, ICDCode


class ICDConcept(DomainModel):
    """
    One ICD-11 concept.

    Represents medical taxonomy only.
    """

    code: ICDCode

    title: str

    description: str | None = None


class TaxonomyCandidate(DomainModel):
    """
    One semantic retrieval result.
    """

    concept: ICDConcept

    similarity_score: float = Field(
        ge=0.0,
        le=1.0,
    )


class ICDSuggestion(DomainModel):
    """
    AI-generated diagnosis recommendation.
    """

    concept: ICDConcept

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    explanation: str
