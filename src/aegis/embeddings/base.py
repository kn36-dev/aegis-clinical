"""
Abstract embedding provider interface.

Embedding providers transform semantic representation documents into
vector documents suitable for semantic search.

Concrete implementations include:

- OpenAI
- Hugging Face
- Ollama
- Voyage AI
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from aegis.indexing.documents import (
        RepresentationDocument,
        VectorDocument,
    )


class EmbeddingProvider(ABC):
    """
    Provider-agnostic embedding interface.
    """

    @abstractmethod
    def embed(
        self,
        document: RepresentationDocument,
    ) -> VectorDocument:
        """
        Embed a single representation document.
        """
        raise NotImplementedError

    def embed_many(
        self,
        documents: Iterable[RepresentationDocument],
    ) -> list[VectorDocument]:
        """
        Embed multiple representation documents.

        The default implementation simply delegates to `embed()`.
        Providers may override this if batch embedding is supported.
        """

        return [self.embed(document) for document in documents]

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """
        Embed a single runtime query string into a vector representation.

        Distinct from `embed()`/`embed_many()`, which operate on the
        offline indexing pipeline's `RepresentationDocument` artifacts.
        A runtime clinical query has no ICD concept identity, so it is
        embedded directly from its normalized text rather than being
        wrapped in a synthetic `RepresentationDocument`. The same
        provider implementation backs both flows to guarantee identical
        vector space semantics between indexing and retrieval.
        """
        raise NotImplementedError
