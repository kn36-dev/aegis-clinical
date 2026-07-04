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
