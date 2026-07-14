"""
OpenAI embedding provider.

Generates embeddings using OpenAI's text embedding models.

Default model:

    text-embedding-3-small
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from openai import OpenAI

from aegis.embeddings.base import EmbeddingProvider
from aegis.indexing.documents import (
    RepresentationDocument,
    VectorDocument,
)

if TYPE_CHECKING:
    from collections.abc import Iterable


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI implementation of the EmbeddingProvider interface.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
    ) -> None:

        self._client = OpenAI(api_key=api_key)
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    def embed(
        self,
        document: RepresentationDocument,
    ) -> VectorDocument:

        response = self._client.embeddings.create(
            model=self._model,
            input=document.text,
        )

        embedding = response.data[0].embedding

        return VectorDocument(
            representation=document,
            embedding=embedding,
        )

    def embed_many(
        self,
        documents: Iterable[RepresentationDocument],
    ) -> list[VectorDocument]:

        if not documents:
            return []

        response = self._client.embeddings.create(
            model=self._model,
            input=[doc.text for doc in documents],
        )

        return [
            VectorDocument(
                representation=doc,
                embedding=item.embedding,
            )
            for doc, item in zip(documents, response.data, strict=True)
        ]

    def embed_query(self, text: str) -> list[float]:

        response = self._client.embeddings.create(
            model=self._model,
            input=text,
        )

        return response.data[0].embedding
