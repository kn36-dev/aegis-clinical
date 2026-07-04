from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from aegis.indexing.documents import (
        VectorDocument,
    )


class VectorUploader:
    """
    Provider-agnostic vector database uploader.

    Concrete implementations may target:

        - Upstash Vector
        - Pinecone
        - Qdrant
        - pgvector
    """

    def upload_many(
        self,
        documents: Iterable[VectorDocument],
    ) -> None:
        raise NotImplementedError
