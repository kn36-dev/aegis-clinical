"""
Canonical indexing artifacts.

These models define the provider-agnostic data contracts that flow through the
offline indexing pipeline.

Pipeline:

    ICDConcept
        ↓
    RepresentationStrategy
        ↓
    RepresentationDocument
        ↓
    EmbeddingProvider
        ↓
    VectorDocument
        ↓
    Vector Database (Upstash)

These models deliberately do NOT depend on LangGraph, repositories,
SQLite, or any embedding/vector provider.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Representation Types
# ============================================================================


class RepresentationType(StrEnum):
    """
    Supported semantic representation strategies.

    Only STRUCTURED_PROSE is implemented in V1.

    Additional strategies remain intentionally deferred until retrieval
    evaluation justifies the added indexing complexity.
    """

    STRUCTURED_PROSE = "structured_prose"

    # Deferred representation strategies
    TITLE = "title"
    HIERARCHY = "hierarchy"
    PARENT_CONTEXT = "parent_context"


# ============================================================================
# Representation Document
# ============================================================================


class RepresentationDocument(BaseModel):
    """
    Canonical artifact produced by a representation strategy.

    This model contains the exact text that will be embedded.

    It intentionally contains no vector, provider-specific identifiers,
    or database implementation details.
    """

    model_config = ConfigDict(frozen=True)

    concept_id: str = Field(description="Stable identifier of the originating ICD concept.")

    representation_type: RepresentationType = Field(
        description="Semantic representation strategy used."
    )

    text: str = Field(description="Canonical text that will be submitted to the embedding model.")

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description=("Optional provider-agnostic metadata associated with this representation."),
    )


# ============================================================================
# Vector Document
# ============================================================================


class VectorDocument(BaseModel):
    """
    Canonical artifact produced after embedding generation.

    This model represents a completed vector record ready to be uploaded
    to any vector database.

    It intentionally remains independent of Upstash or any specific
    vector storage implementation.
    """

    model_config = ConfigDict(frozen=True)

    representation: RepresentationDocument = Field(description="Original representation document.")

    embedding: list[float] = Field(
        description="Embedding vector generated from the representation text."
    )
