"""
Compiled local vector index for ``AEGIS_PROFILE=demo-local``.

Phase 1 (offline knowledge compilation) offline-compiles the real
ICD-11 taxonomy into a queryable vector index without any external
vector database. This reuses the exact same ``IndexingPipeline`` /
``RepresentationBuilder`` / ``EmbeddingProvider`` boundary
``scripts/upload_index.py`` uses to build the real Upstash-backed
index -- the only difference is the terminal artifact: a JSON file on
disk instead of a live Upstash Vector index. There is no
demo-local-specific indexing logic here, only a different sink plus
staleness detection so this compile step runs once per taxonomy
version rather than on every process start (matching Phase 1's
"runs only when the ICD-11 taxonomy changes" doctrine even though
``AEGIS_PROFILE=demo-local`` triggers it inline from the API bootstrap
rather than a standalone offline job).

The compiled artifact is a generated build output, not application
state or checked-in data -- it lives under ``.artifacts/`` (already
gitignored, alongside ``.artifacts/evaluations/``), never under
``data/`` or ``state/``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from aegis.common.logging import get_logger
from aegis.database.repositories.icd_repository import ICDRepository
from aegis.indexing.builders import RepresentationBuilder
from aegis.indexing.documents import VectorDocument
from aegis.indexing.pipeline import IndexingPipeline
from aegis.indexing.representations.structured_prose import StructuredProseRepresentation
from aegis.vectorstores.local import LocalVectorStore

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Sequence

    from aegis.database.repositories.models import ICDTaxonomyRecord
    from aegis.embeddings.base import EmbeddingProvider

logger = get_logger(__name__)

DEFAULT_LOCAL_INDEX_DIR = Path(".artifacts/local_vector_index")

_MANIFEST_FILENAME = "manifest.json"
_VECTORS_FILENAME = "vectors.json"


@dataclass(frozen=True)
class LocalIndexManifest:
    """
    Fingerprint of a compiled local vector index artifact.

    Every field must match the current taxonomy content and embedding
    configuration for a cached artifact to be reused; any mismatch
    (a taxonomy row added/edited/removed, or the embedding model/
    dimensions changing) triggers a full recompile rather than
    silently serving a stale or vector-space-incompatible index.
    """

    taxonomy_row_count: int
    taxonomy_hash: str
    embedding_model: str
    embedding_dimensions: int
    representation_type: str


def _hash_taxonomy(records: Sequence[ICDTaxonomyRecord]) -> str:
    """
    Deterministic content hash of the taxonomy, independent of SQLite
    row order -- detects any addition, removal, or edit to a taxonomy
    row that would change what the compiled index should contain.
    """
    digest = hashlib.sha256()
    for record in sorted(records, key=lambda r: r.code):
        digest.update(record.code.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(record.title.encode("utf-8"))
        digest.update(b"\x00")
        digest.update((record.context_path or "").encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()


def _build_manifest(
    records: Sequence[ICDTaxonomyRecord],
    embedding_model: str,
    embedding_dimensions: int,
) -> LocalIndexManifest:
    return LocalIndexManifest(
        taxonomy_row_count=len(records),
        taxonomy_hash=_hash_taxonomy(records),
        embedding_model=embedding_model,
        embedding_dimensions=embedding_dimensions,
        representation_type=StructuredProseRepresentation().representation_type.value,
    )


def _load_manifest(index_dir: Path) -> LocalIndexManifest | None:
    path = index_dir / _MANIFEST_FILENAME
    if not path.exists():
        return None
    return LocalIndexManifest(**json.loads(path.read_text()))


def _load_vector_documents(index_dir: Path) -> list[VectorDocument]:
    raw = json.loads((index_dir / _VECTORS_FILENAME).read_text())
    return [VectorDocument.model_validate(entry) for entry in raw]


def _save_artifact(
    index_dir: Path,
    manifest: LocalIndexManifest,
    vector_documents: list[VectorDocument],
) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    (index_dir / _VECTORS_FILENAME).write_text(
        json.dumps([document.model_dump(mode="json") for document in vector_documents])
    )
    (index_dir / _MANIFEST_FILENAME).write_text(json.dumps(asdict(manifest), indent=2))


def compile_or_load_local_vector_store(
    connection: sqlite3.Connection,
    embedding_provider: EmbeddingProvider,
    *,
    embedding_model: str,
    embedding_dimensions: int,
    index_dir: Path = DEFAULT_LOCAL_INDEX_DIR,
) -> LocalVectorStore:
    """
    Load the compiled local vector index from ``index_dir`` if its
    manifest matches the current taxonomy and embedding configuration,
    otherwise compile it from scratch via the real offline
    ``IndexingPipeline`` and persist it for next time.

    Embedding ~15k taxonomy rows with a local SentenceTransformers model
    is CPU-bound and takes real wall-clock time (minutes, not seconds)
    -- this function pays that cost at most once per taxonomy version,
    never on every process start/reload, by persisting the result and
    validating a manifest before reusing it.
    """
    repository = ICDRepository(connection)
    records = repository.list_all()
    manifest = _build_manifest(records, embedding_model, embedding_dimensions)

    cached_manifest = _load_manifest(index_dir)
    if cached_manifest == manifest:
        logger.info(
            "Loading compiled local vector index | dir=%s | rows=%d",
            index_dir,
            manifest.taxonomy_row_count,
        )
        vector_documents = _load_vector_documents(index_dir)
    else:
        logger.info(
            "%s local vector index at %s -- compiling %d taxonomy rows with %s "
            "(one-time cost; subsequent runs load the cached artifact until the "
            "taxonomy or embedding configuration changes).",
            "No compiled" if cached_manifest is None else "Stale compiled",
            index_dir,
            manifest.taxonomy_row_count,
            embedding_model,
        )
        builder = RepresentationBuilder(strategy=StructuredProseRepresentation())
        pipeline = IndexingPipeline(repository, builder, embedding_provider)
        vector_documents = pipeline.run()
        _save_artifact(index_dir, manifest, vector_documents)
        logger.info("Compiled and cached local vector index | rows=%d", len(vector_documents))

    store = LocalVectorStore()
    store.index_many(vector_documents)
    return store
