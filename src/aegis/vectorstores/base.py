from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from aegis.indexing.documents import VectorDocument


class VectorStore(ABC):
    """
    Provider-agnostic vector database interface.

    Concrete implementations may target:

        - Upstash Vector
        - Pinecone
        - Qdrant
        - pgvector
    """

    @abstractmethod
    def index(
        self,
        document: VectorDocument,
    ) -> None:
        """
        Insert or update a single vector.
        """
        raise NotImplementedError

    def index_many(
        self,
        documents: Iterable[VectorDocument],
    ) -> None:
        """
        Default bulk implementation.

        Concrete providers may override this for native
        batch APIs.
        """

        for document in documents:
            self.index(document)

    @abstractmethod
    def delete(
        self,
        concept_id: str,
    ) -> None:
        """
        Delete a vector by concept identifier.
        """
        raise NotImplementedError
