from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

from aegis.common.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from pathlib import Path

    from aegis.indexing.documents import VectorDocument
    from aegis.vectorstores.base import VectorStore


# -----------------------------------------------------------------------------
# Checkpoint
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class UploadCheckpoint:
    next_index: int
    batch_size: int
    total: int
    completed: bool = False


class CheckpointStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> Optional[UploadCheckpoint]:
        if not self.path.exists():
            return None

        data = json.loads(self.path.read_text())

        return UploadCheckpoint(
            next_index=data["next_index"],
            batch_size=data["batch_size"],
            total=data["total"],
            completed=data.get("completed", False),
        )

    def save(self, checkpoint: UploadCheckpoint) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self.path.write_text(
            json.dumps(
                {
                    "next_index": checkpoint.next_index,
                    "batch_size": checkpoint.batch_size,
                    "total": checkpoint.total,
                    "completed": checkpoint.completed,
                },
                indent=2,
            )
        )


# -----------------------------------------------------------------------------
# Upload Job
# -----------------------------------------------------------------------------


class UploadJob:
    """
    Uploads VectorDocuments into a VectorStore.

    Responsibilities
    ----------------
    - batching
    - checkpoint persistence
    - resumable execution
    - limiting work performed in a single execution

    Does NOT know:
    - embeddings
    - representation strategies
    - Upstash
    - LangGraph
    """

    def __init__(
        self,
        vector_store: VectorStore,
        checkpoint_store: CheckpointStore,
        batch_size: int = 500,
        max_documents_per_run: int | None = None,
    ):
        self.vector_store = vector_store
        self.checkpoint_store = checkpoint_store
        self.batch_size = batch_size
        self.max_documents_per_run = max_documents_per_run

    def run(self, documents: List[VectorDocument]) -> None:
        checkpoint = self.checkpoint_store.load()

        total = len(documents)

        if checkpoint is None:
            checkpoint = UploadCheckpoint(
                next_index=0,
                batch_size=self.batch_size,
                total=total,
            )

        if checkpoint.completed:
            logger.info("Upload already completed.")
            return

        start = checkpoint.next_index

        execution_limit = total

        if self.max_documents_per_run is not None:
            execution_limit = min(
                total,
                start + self.max_documents_per_run,
            )

        logger.info(
            "Starting upload job | start=%d limit=%d total=%d batch_size=%d",
            start,
            execution_limit,
            total,
            self.batch_size,
        )

        while start < execution_limit:
            end = min(
                start + self.batch_size,
                execution_limit,
            )

            batch = documents[start:end]

            logger.info(
                "Uploading batch [%d:%d]",
                start,
                end,
            )

            self.vector_store.index_many(batch)

            start = end

            completed = start >= total

            checkpoint = UploadCheckpoint(
                next_index=start,
                batch_size=self.batch_size,
                total=total,
                completed=completed,
            )

            self.checkpoint_store.save(checkpoint)

            logger.info(
                "Progress %d/%d",
                start,
                total,
            )

        logger.info("Execution finished.")
