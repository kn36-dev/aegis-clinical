# src/aegis/scripts/upload_index.py

import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

from aegis.common.logging import configure_logging, get_logger
from aegis.database.repositories.icd_repository import ICDRepository
from aegis.embeddings.sentence_transformers import SentenceTransformersEmbeddingProvider
from aegis.indexing.builders import RepresentationBuilder
from aegis.indexing.pipeline import IndexingPipeline
from aegis.indexing.representations.structured_prose import StructuredProseRepresentation
from aegis.vectorstores.upstash import UpstashVectorStore

load_dotenv()

configure_logging()
logger = get_logger(__name__)


def main():
    connection = sqlite3.connect(os.getenv("CLINICAL_DB_PATH", "data/clinical_registry.db"))

    repository = ICDRepository(connection=connection)
    strategy = StructuredProseRepresentation()
    builder = RepresentationBuilder(strategy=strategy)
    embedder = SentenceTransformersEmbeddingProvider(model_name="BAAI/bge-large-en-v1.5")

    vector_store = UpstashVectorStore(
        url=os.environ["UPSTASH_VECTOR_REST_URL"],
        token=os.environ["UPSTASH_VECTOR_REST_TOKEN"],
    )

    pipeline = IndexingPipeline(
        repository=repository,
        builder=builder,
        embedder=embedder,
    )

    logger.info("Starting offline index build")
    logger.info(
        "Repository DB path: %s", os.getenv("CLINICAL_DB_PATH", "data/clinical_registry.db")
    )
    logger.info("Embedding model: %s", embedder.model)
    logger.info("Vector store URL configured: %s", bool(os.getenv("UPSTASH_VECTOR_REST_URL")))

    vector_documents = pipeline.run()

    logger.info("Generated %d vector documents", len(vector_documents))

    for doc in vector_documents[:5]:
        logger.info(
            "Preview | concept=%s | embedding_dim=%d | representation_text=%s",
            doc.representation.concept_id,
            len(doc.embedding),
            doc.representation.text,
        )
        logger.info(
            "Preview metadata | concept=%s | metadata=%s",
            doc.representation.concept_id,
            doc.representation.metadata,
        )

    from aegis.jobs.upload_job import CheckpointStore, UploadJob

    job = UploadJob(
        vector_store=vector_store,
        checkpoint_store=CheckpointStore(Path("./state/upload_checkpoint.json")),
        batch_size=10,
        max_documents_per_run=10,
    )

    logger.info(
        "Upload config | batch_size=%d | max_documents_per_run=%d",
        job.batch_size,
        job.max_documents_per_run,
    )

    job.run(vector_documents)


if __name__ == "__main__":
    main()
