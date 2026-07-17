# src/aegis/embeddings/sentence_transformers.py

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Iterable

from sentence_transformers import SentenceTransformer

from aegis.embeddings.base import EmbeddingProvider
from aegis.indexing.documents import RepresentationDocument, VectorDocument


class SentenceTransformersEmbeddingProvider(EmbeddingProvider):
    """
    Local embedding provider using SentenceTransformers.

    Default model:
        BAAI/bge-large-en-v1.5
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-large-en-v1.5",
    ) -> None:

        self._model = SentenceTransformer(model_name)
        self._model_name = model_name

        # single-time invariant (NO runtime per-vector checks needed)
        self._embedding_dim = self._model.get_embedding_dimension()

    @property
    def model(self) -> str:
        return self._model_name

    def embed(self, document: RepresentationDocument) -> VectorDocument:
        embedding = self._model.encode(document.text).tolist()

        return VectorDocument(
            representation=document,
            embedding=embedding,
        )

    def embed_many(
        self,
        documents: Iterable[RepresentationDocument],
    ) -> list[VectorDocument]:
        """
        Batch embedding optimized for local inference.
        """

        docs = list(documents)

        if not docs:
            return []

        embeddings = self._model.encode(
            [doc.text for doc in docs],
            batch_size=64,
            show_progress_bar=True,
        )

        return [
            VectorDocument(
                representation=doc,
                embedding=emb.tolist(),
            )
            for doc, emb in zip(docs, embeddings, strict=True)
        ]

    def embed_query(self, text: str) -> list[float]:
        embedding = self._model.encode(text).tolist()
        return cast("list[float]", embedding)
