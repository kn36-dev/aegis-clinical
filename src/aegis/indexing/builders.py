"""
Representation Builder.

Coordinates representation generation while remaining completely
agnostic to the specific semantic strategy employed.

Pipeline

    ICDTaxonomyRecord
            │
            ▼
    RepresentationBuilder
            │
            ▼
    RepresentationStrategy
            │
            ▼
    RepresentationDocument
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aegis.database.repositories.models import ICDTaxonomyRecord
    from aegis.indexing.documents import RepresentationDocument
    from aegis.indexing.representations.base import (
        RepresentationStrategy,
    )


class RepresentationBuilder:
    """
    Orchestrates semantic representation generation.

    The builder itself contains no representation logic.

    Instead it delegates the transformation to the configured
    RepresentationStrategy.
    """

    def __init__(
        self,
        strategy: RepresentationStrategy,
    ):
        self._strategy = strategy

    @property
    def strategy(self) -> RepresentationStrategy:
        """
        The active semantic representation strategy.
        """
        return self._strategy

    def build(
        self,
        record: ICDTaxonomyRecord,
    ) -> RepresentationDocument:
        """
        Generate the canonical representation document
        for a taxonomy record.
        """
        return self._strategy.build(record)

    def build_many(
        self,
        records: list[ICDTaxonomyRecord],
    ) -> list[RepresentationDocument]:
        """
        Generate representation documents for multiple ICD concepts.
        """

        return [self.build(record) for record in records]
