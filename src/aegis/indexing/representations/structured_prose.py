# ============================================================================
# Structured Prose Strategy
# ============================================================================

import re

from aegis.common.logging import get_logger
from aegis.database.repositories.models import ICDTaxonomyRecord
from aegis.indexing.documents import (
    RepresentationDocument,
    RepresentationType,
)
from aegis.indexing.representations.base import RepresentationStrategy

logger = get_logger(__name__)


class StructuredProseRepresentation(RepresentationStrategy):
    """
    Produces a compact structured clinical prose representation.

    The embedding text is intentionally limited to ontology-relevant details:
    - ICD code
    - normalized clinical term
    - classification hierarchy
    - classification kind

    Irrelevant implementation details such as block_id, grouping, or chapter
    are excluded from the text that will be embedded.
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
        title_text = normalized_title or record.title or "[missing title]"

        parts: list[str] = [
            f"ICD-11 Code: {record.code}",
            f"Clinical Term: {title_text}",
        ]

        if record.context_path:
            hierarchy_text = record.context_path.replace(" > ", "; ")
            parts.append(f"Classification Hierarchy: {hierarchy_text}")

        if record.class_kind:
            parts.append(f"Classification: {record.class_kind}")

        text = " ".join(parts)

        logger.info(
            "StructuredProse build | concept=%s | text=%s",
            record.code,
            text,
        )

        return RepresentationDocument(
            concept_id=record.code,
            representation_type=self.representation_type,
            text=text,
            metadata={
                "code": record.code,
                "title": title_text,
                "class_kind": record.class_kind,
                "context_path": record.context_path,
            },
        )
