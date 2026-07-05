# ============================================================================
# Structured Prose Strategy
# ============================================================================

import re

from aegis.database.repositories.models import ICDTaxonomyRecord
from aegis.indexing.documents import (
    RepresentationDocument,
    RepresentationType,
)
from aegis.indexing.representations.base import RepresentationStrategy


class StructuredProseRepresentation(RepresentationStrategy):
    """
    Produces a structured clinical prose representation.

    This is intentionally the only representation strategy used in V1.

    The formatting attempts to expose clinically meaningful information
    while remaining natural language friendly for embedding models.
    """

    @property
    def representation_type(self) -> RepresentationType:
        return RepresentationType.STRUCTURED_PROSE

    def _normalize_title(self, title: str | None) -> str | None:
        if not title:
            return None

        cleaned = re.sub(r"^\s*(?:-\s*)+", "", title).strip()
        return cleaned or None

    def build(
        self,
        record: ICDTaxonomyRecord,
    ) -> RepresentationDocument:

        normalized_title = self._normalize_title(record.title)

        lines: list[str] = [
            f"ICD-11 Code: {record.code}",
            f"Title: {normalized_title or record.title or '[missing title]'}",
        ]

        if record.context_path:
            lines.append(f"Hierarchy: {record.context_path}")

        if record.class_kind:
            lines.append(f"Classification: {record.class_kind}")

        if record.block_id:
            lines.append(f"Block: {record.block_id}")

        if record.chapter_no:
            lines.append(f"Chapter: {record.chapter_no}")

        if record.is_leaf is not None:
            lines.append(f"Is Leaf: {'yes' if record.is_leaf else 'no'}")

        if record.is_residual is not None:
            lines.append(f"Is Residual: {'yes' if record.is_residual else 'no'}")

        if record.grouping_1:
            lines.append(f"Grouping 1: {record.grouping_1}")

        if record.grouping_2:
            lines.append(f"Grouping 2: {record.grouping_2}")

        text = "\n".join(lines)

        return RepresentationDocument(
            concept_id=record.code,
            representation_type=self.representation_type,
            text=text,
            metadata={
                "code": record.code,
                "title": normalized_title or record.title or "",
                "class_kind": record.class_kind,
                "context_path": record.context_path,
                "block_id": record.block_id,
                "chapter_no": record.chapter_no,
                "is_leaf": record.is_leaf,
                "is_residual": record.is_residual,
                "grouping_1": record.grouping_1,
                "grouping_2": record.grouping_2,
            },
        )
