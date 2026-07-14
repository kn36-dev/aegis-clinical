# RetrievalRequest / RetrievalResult / RetrievalCandidate
#
# Shape defined by runtime_domain_contracts/retrieval_request.md,
# retrieval_result.md, and retrieval_candidate.md (authoritative).
#
# RetrievalRequest owns
#
# clinical_note (reference to the originating immutable ClinicalNote)
# normalized_note (the deterministic query representation)
# top_k (bounded candidate limit)
# similarity_threshold (optional similarity constraint)
#
# RetrievalRequest should not contain
#
# embedding vectors, Redis keys, cache lookup results, Upstash payloads,
# vector identifiers, similarity scores, retrieval candidates, workflow state
#
# RetrievalCandidate owns
#
# icd_code, title, hierarchy_context, chapter_number,
# semantic_representation, similarity_score, retrieval_metadata
#
# One candidate = one ICD code; RetrievalResult enforces no duplicates.
#
# RetrievalResult owns
#
# normalized_note (query reference), candidates, retrieval_metadata
#
# Should not contain
#
# clinical diagnosis, confidence score, physician decision, LLM reasoning,
# final ranking, ontology interpretation, ICD selection, workflow state
#
# Note on scope: the contracts mention "retrieval mode" as a typical
# RetrievalRequest field alongside top_k and similarity constraints, but
# no retrieval mode currently exists to select between (only vector
# similarity search is implemented). That field is intentionally omitted
# until a second retrieval mode exists to justify it.
#
# Note on retrieval_metadata: the contracts describe this as
# provider-generated metadata for evaluation/debugging (e.g. similarity
# distance, vector namespace, retrieval configuration) rather than a
# fixed shape, so it is modeled as an open dict rather than a fixed set
# of fields.

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from aegis.models.base import DomainModel, ICDCode
from aegis.models.clinical_note import ClinicalNote
from aegis.models.normalized_clinical_note import NormalizedClinicalNote


class RetrievalRequest(DomainModel):
    """
    Deterministic request to the semantic retrieval subsystem.

    Created by ``RetrievalService`` callers after deterministic
    preprocessing (normalization) has completed. Expresses *what*
    should be retrieved — the query representation and bounds — without
    exposing embedding models, vector databases, or caching technology.
    """

    clinical_note: ClinicalNote
    normalized_note: NormalizedClinicalNote
    top_k: int = Field(gt=0)
    similarity_threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class RetrievalCandidate(DomainModel):
    """
    One ICD-11 taxonomy concept returned by semantic retrieval.

    ``similarity_score`` represents semantic proximity only and must
    never be interpreted as clinical confidence.
    """

    icd_code: ICDCode
    title: str
    hierarchy_context: str | None = None
    chapter_number: str | None = None
    semantic_representation: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    retrieval_metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(DomainModel):
    """
    Raw semantic retrieval output, produced exclusively by
    ``RetrievalService`` after translating provider-specific vector
    search output into canonical domain objects.

    Represents bounded evidence for downstream ranking and reasoning —
    not a diagnosis, confidence estimate, or final ICD selection.
    """

    normalized_note: NormalizedClinicalNote
    candidates: list[RetrievalCandidate]
    retrieval_metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _no_duplicate_icd_codes(self) -> RetrievalResult:
        codes = [candidate.icd_code for candidate in self.candidates]
        if len(codes) != len(set(codes)):
            raise ValueError("RetrievalResult candidates must not contain duplicate ICD codes.")
        return self
