"""
Local retrieval-evaluation index construction.

Pure wiring: seeds a temporary, throwaway SQLite database from the eval
fixture CSV (``data/eval_icd_fixture.csv`` -- see its README for scope and
provenance) via the existing ``aegis.database.seeds.seed_icd11``, runs the
existing ``aegis.indexing.pipeline.IndexingPipeline`` over it, and loads
the resulting vectors into a ``LocalVectorStore`` / ``LocalVectorQueryProvider``
pair. Introduces no new representation, embedding, or ranking logic --
every step delegates to an existing offline-indexing-pipeline component;
this module only sequences them for the local/CI evaluation mode.

Never touches ``data/clinical_registry.db`` -- the temp database lives
under a ``tempfile.TemporaryDirectory`` and is discarded once indexing
completes.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from aegis.database.repositories.icd_repository import ICDRepository
from aegis.database.seeds import seed_icd11
from aegis.indexing.builders import RepresentationBuilder
from aegis.indexing.pipeline import IndexingPipeline
from aegis.indexing.representations.structured_prose import StructuredProseRepresentation
from aegis.retrieval.providers.local import LocalVectorQueryProvider
from aegis.vectorstores.local import LocalVectorStore

if TYPE_CHECKING:
    from aegis.embeddings.base import EmbeddingProvider


def build_local_vector_query_provider(
    fixture_csv_path: str | Path,
    embedding_provider: EmbeddingProvider,
) -> LocalVectorQueryProvider:
    """
    Build a ``LocalVectorQueryProvider`` populated from ``fixture_csv_path``.

    Seeds a throwaway SQLite database in a temp directory using the same
    ``seed_icd11`` the production ``aegis-db seed`` CLI command uses, then
    runs the real offline indexing pipeline (``RepresentationBuilder`` +
    ``IndexingPipeline``) against it with the caller-supplied
    ``embedding_provider``.
    """
    with tempfile.TemporaryDirectory(prefix="aegis-eval-fixture-") as tmp_dir:
        db_path = Path(tmp_dir) / "eval_fixture.db"
        seed_icd11(db_path=db_path, csv_path=Path(fixture_csv_path))

        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        try:
            repository = ICDRepository(connection)
            builder = RepresentationBuilder(strategy=StructuredProseRepresentation())
            pipeline = IndexingPipeline(repository, builder, embedding_provider)
            vector_documents = pipeline.run()
        finally:
            connection.close()

    store = LocalVectorStore()
    store.index_many(vector_documents)
    return LocalVectorQueryProvider(store)
