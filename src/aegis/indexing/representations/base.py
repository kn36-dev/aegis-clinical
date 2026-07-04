"""
Semantic representation strategies for ICD-11 concepts.

A representation strategy transforms an ICD taxonomy record into the
canonical text that will be embedded into the vector database.

Pipeline

    ICDTaxonomyRecord
            │
            ▼
    RepresentationStrategy
            │
            ▼
    RepresentationDocument
            │
            ▼
    Embedding Provider
            │
            ▼
    VectorDocument

Representation strategies are intentionally:

- deterministic
- provider-agnostic
- side-effect free
- independent of LangGraph
- independent of repositories
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aegis.database.repositories.models import ICDTaxonomyRecord
    from aegis.indexing.documents import (
        RepresentationDocument,
        RepresentationType,
    )


class RepresentationStrategy(ABC):
    """
    Abstract base class for all semantic representation strategies.

    A strategy receives an ICD taxonomy record and produces the exact
    text that should be embedded.
    """

    @property
    @abstractmethod
    def representation_type(self) -> RepresentationType:
        """Type of semantic representation produced."""
        raise NotImplementedError

    @abstractmethod
    def build(
        self,
        record: ICDTaxonomyRecord,
    ) -> RepresentationDocument:
        """
        Produce a canonical representation document.
        """
        raise NotImplementedError
