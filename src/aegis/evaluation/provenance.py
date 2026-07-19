"""
ProvenanceMetadata

Reproducibility stamp attached to every evaluation report: which code,
dataset, and configuration produced this run, and against which model
and retrieval backend. None of this is business logic -- it is
orchestration bookkeeping so a report can be trusted (or reproduced)
without cross-referencing a separate lab notebook.
"""

from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel


class ProvenanceMetadata(BaseModel):
    """
    Reproducibility metadata for one evaluation report.

    ``git_commit`` is ``None`` when the working tree is not a git
    repository or the lookup otherwise fails -- best-effort, never fatal
    to the evaluation run itself.
    """

    git_commit: str | None
    dataset_path: str
    dataset_hash: str
    config_hash: str
    retrieval_backend: str
    model_provider_info: str
    generated_at: datetime


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _current_git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def build_provenance(
    *,
    dataset_path: str | Path,
    config_path: str | Path,
    retrieval_backend: str,
    model_provider_info: str,
) -> ProvenanceMetadata:
    """Build the ``ProvenanceMetadata`` for one evaluation run."""
    return ProvenanceMetadata(
        git_commit=_current_git_commit(),
        dataset_path=str(dataset_path),
        dataset_hash=_sha256_file(dataset_path),
        config_hash=_sha256_file(config_path),
        retrieval_backend=retrieval_backend,
        model_provider_info=model_provider_info,
        generated_at=datetime.now(timezone.utc),
    )
