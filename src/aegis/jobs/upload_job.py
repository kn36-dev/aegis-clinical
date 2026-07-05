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

# ----------------------------
# Checkpoint
# ----------------------------


@dataclass(frozen=True)
class UploadCheckpoint:
    """
    Tracks progress of a long-running vector upload job.

    This is intentionally minimal:
    - index-based progress (stable across runs)
    - no dependency on external systems
    """

    next_index: int
    batch_size: int
    total: int
    completed: bool = False


class CheckpointStore:
    """
    File-based checkpoint persistence.

    Simple, deterministic, and sufficient for offline indexing jobs.
    """

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


# ----------------------------
# Upload Job
# ----------------------------


class UploadJob:
    """
    Orchestrates batched uploads of VectorDocuments into a VectorStore.

    Responsibilities:
    - batching
    - checkpointing
    - resuming
    - enforcing external constraints (e.g. Upstash limits)

    Does NOT:
    - build embeddings
    - build representations
    - decide vector schema
    """

    def __init__(
        self,
        vector_store: VectorStore,
        checkpoint_store: CheckpointStore,
        batch_size: int = 500,
    ):
        self.vector_store = vector_store
        self.checkpoint_store = checkpoint_store
        self.batch_size = batch_size

    def run(self, documents: List[VectorDocument]) -> None:
        logger.info(f"Starting upload job | total={len(documents)} | batch_size={self.batch_size}")

        checkpoint = self.checkpoint_store.load()

        start = checkpoint.next_index if checkpoint else 0
        total = len(documents)

        if checkpoint is None:
            checkpoint = UploadCheckpoint(
                next_index=0,
                batch_size=self.batch_size,
                total=total,
            )

        while start < total:
            end = min(start + self.batch_size, total)
            batch = documents[start:end]

            logger.info(f"Uploading batch | start={start} end={end} total={total}")
            # ---- Upsert batch ----
            self.vector_store.index_many(batch)

            start = end

            # ---- Save checkpoint ----
            checkpoint = UploadCheckpoint(
                next_index=start,
                batch_size=self.batch_size,
                total=total,
                completed=(start >= total),
            )

            self.checkpoint_store.save(checkpoint)

            logger.info(f"Uploaded batch successfully | up_to={start}")
            print(f"[UploadJob] Uploaded {start}/{total}")

        logger.info("Upload job completed successfully")
        print("[UploadJob] Completed")
