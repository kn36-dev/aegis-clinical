"""
Abstract vector query provider interface.

Read-only runtime counterpart to ``aegis.vectorstores.base.VectorStore``.
``VectorStore`` is the offline knowledge-compilation write path (index,
index_many, delete) used exclusively by the indexing pipeline.
``VectorQueryProvider`` is the runtime read path used exclusively by
``RetrievalService``: given a query embedding, return the nearest
stored vectors. The two abstractions are kept separate so the
write-only offline adapter never needs to expose, or be coupled to,
query behavior, and vice versa.

Concrete implementations include:

- Upstash Vector
- Pinecone
- Qdrant
- pgvector
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict


class VectorMatch(BaseModel):
    """
    Provider-agnostic raw result of a single vector similarity query.

    Deliberately mirrors the shape vector databases return (id, score,
    metadata) rather than any AEGIS domain contract —
    ``RetrievalService`` is responsible for translating this into a
    canonical ``RetrievalCandidate``.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    score: float
    metadata: dict[str, Any]


class VectorQueryProvider(ABC):
    """
    Provider-agnostic semantic query interface.
    """

    @abstractmethod
    def query(
        self,
        embedding: list[float],
        top_k: int,
    ) -> list[VectorMatch]:
        """
        Return the ``top_k`` nearest stored vectors to ``embedding``.
        """
        raise NotImplementedError
