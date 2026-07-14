"""
RetrievalService

Implements application_service_contracts/retrieval_service.md.

Owns translation of a ``RetrievalRequest`` — a ``NormalizedClinicalNote``
plus retrieval configuration — into a ``RetrievalResult``: a bounded,
provider-agnostic collection of semantically similar ICD-11
``RetrievalCandidate`` objects.

This is evidence acquisition, not clinical reasoning. The service never
ranks candidates by clinical correctness, estimates confidence, selects
a diagnosis, or constructs reasoning/prompt context — see
application_service_contracts/retrieval_service.md for the full
boundary. A ``similarity_score`` represents semantic proximity only and
must never be interpreted as clinical confidence.

This module intentionally has no dependency on Redis, SQLite, LLM
providers, CrewAI, or LangGraph. Embedding generation is expressed only
through the ``EmbeddingProvider`` abstraction, and vector similarity
search only through the ``VectorQueryProvider`` abstraction; concrete
adapters are injected by the caller.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from aegis.models.retrieval import RetrievalCandidate, RetrievalRequest, RetrievalResult

if TYPE_CHECKING:
    from aegis.embeddings.base import EmbeddingProvider
    from aegis.retrieval.providers.base import VectorMatch, VectorQueryProvider


class RetrievalService(ABC):
    """
    Application service boundary that answers "which ICD-11 concepts
    are semantically similar to this clinical observation?" — never
    "which concept is clinically correct?".

    Performs no clinical ranking, diagnosis, confidence estimation, or
    prompt/context assembly — see
    application_service_contracts/retrieval_service.md for the full
    boundary.
    """

    @abstractmethod
    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """Produce the bounded ``RetrievalResult`` for ``request``."""
        raise NotImplementedError


class DefaultRetrievalService(RetrievalService):
    """
    Concrete ``RetrievalService`` implementation.

    Dependencies are injected so the service remains deterministic and
    independently testable: given the same ``RetrievalRequest``,
    embedding provider, and query provider, it always produces the same
    ``RetrievalResult``.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        query_provider: VectorQueryProvider,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._query_provider = query_provider

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        query_embedding = self._embedding_provider.embed_query(
            request.normalized_note.normalized_text
        )

        matches = self._query_provider.query(
            embedding=query_embedding,
            top_k=request.top_k,
        )

        candidates = [
            self._translate(match)
            for match in matches
            if request.similarity_threshold is None or match.score >= request.similarity_threshold
        ]

        return RetrievalResult(
            normalized_note=request.normalized_note,
            candidates=candidates,
            retrieval_metadata={
                "top_k": request.top_k,
                "similarity_threshold": request.similarity_threshold,
            },
        )

    @staticmethod
    def _translate(match: VectorMatch) -> RetrievalCandidate:
        """
        Translate a provider-specific ``VectorMatch`` into a canonical
        ``RetrievalCandidate``.

        ``metadata`` is expected to carry the fields written by the
        offline indexing pipeline's ``RepresentationMetadata``
        (``aegis.indexing.documents``) — ``code`` and ``title`` are
        required there for every indexed concept, so a missing key here
        indicates a corrupted index entry and is allowed to raise
        rather than silently fabricating a candidate.
        """
        metadata = match.metadata

        return RetrievalCandidate(
            icd_code=metadata["code"],
            title=metadata["title"],
            hierarchy_context=metadata.get("context_path"),
            chapter_number=metadata.get("chapter_number"),
            semantic_representation=metadata.get("embedded_text", ""),
            similarity_score=match.score,
            retrieval_metadata=metadata,
        )
