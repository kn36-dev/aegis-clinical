"""
Offline ICD-11 indexing pipeline.

Coordinates the deterministic construction of the semantic search index.

Pipeline

    ICDRepository
            │
            ▼
    ICDTaxonomyRecord
            │
            ▼
    RepresentationBuilder
            │
            ▼
    RepresentationDocument
            │
            ▼
    EmbeddingProvider
            │
            ▼
    VectorDocument
            │
            ▼
    VectorUploader

Unlike the online clinical workflow, this pipeline executes as an
offline batch process and therefore intentionally does not use
LangGraph.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aegis.database.repositories.icd_repository import ICDRepository
    from aegis.database.repositories.models import ICDTaxonomyRecord
    from aegis.indexing.builders import RepresentationBuilder
    from aegis.indexing.documents import (
        RepresentationDocument,
        VectorDocument,
    )

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.aegis.embeddings.base import EmbeddingProvider
    from src.aegis.vectorstores.base import VectorUploader


class IndexingPipeline:
    """
    Coordinates the offline indexing workflow.

    This class intentionally contains no business logic.

    Each stage of the indexing pipeline is delegated to a dedicated
    component with a single responsibility.
    """

    def __init__(
        self,
        repository: ICDRepository,
        builder: RepresentationBuilder,
        embedder: EmbeddingProvider,
        uploader: VectorUploader,
    ) -> None:
        self._repository = repository
        self._builder = builder
        self._embedder = embedder
        self._uploader = uploader

    def build_representation_documents(
        self,
    ) -> list[RepresentationDocument]:
        """
        Load all ICD taxonomy records and generate representation
        documents.
        """

        records: list[ICDTaxonomyRecord] = self._repository.list_all()

        return self._builder.build_many(records)

    def build_vector_documents(
        self,
    ) -> list[VectorDocument]:
        """
        Generate vector documents ready for upload.
        """

        representations = self.build_representation_documents()

        return self._embedder.embed_many(representations)

    def upload(
        self,
    ) -> None:
        """
        Upload all generated vectors into the configured vector store.
        """

        vectors = self.build_vector_documents()

        self._uploader.upload_many(vectors)

    def run(self) -> None:
        """
        Execute the complete offline indexing pipeline.
        """

        self.upload()
