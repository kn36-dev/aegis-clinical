# ============================================================================
# Structured Prose Strategy
# ============================================================================


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

    def build(
        self,
        record: ICDTaxonomyRecord,
    ) -> RepresentationDocument:

        lines: list[str] = [
            f"ICD-11 Code: {record.code}",
            f"Title: {record.title}",
        ]

        if record.context_path:
            lines.append(f"Hierarchy: {record.context_path}")

        if record.class_kind:
            lines.append(f"Classification: {record.class_kind}")

        text = "\n".join(lines)

        return RepresentationDocument(
            concept_id=record.code,
            representation_type=self.representation_type,
            text=text,
            metadata={
                "code": record.code,
                "title": record.title,
                "class_kind": record.class_kind,
            },
        )
