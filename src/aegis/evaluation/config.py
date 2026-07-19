"""
EvaluationConfig

Human-authored evaluation behaviour, loaded from YAML (``config/evaluation.yaml``
/ ``config/evaluation.production.yaml``) -- deliberately separate from
secrets, which remain in ``.env``/``AppSettings`` (``aegis.config``) and are
never duplicated here. This module only shapes and validates configuration;
provider/service construction from it lives in ``aegis.evaluation.runner``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field

from aegis.evaluation.rate_limiter import RateLimitConfig
from aegis.models.base import DomainModel


class RetrievalEvalConfig(DomainModel):
    """Retrieval-evaluation-specific configuration."""

    # "local": deterministic, CI-safe, uses the small fixture index built by
    # aegis.evaluation.local_index -- see config/evaluation.yaml.
    # "production": the real Upstash Vector index via aegis.api.bootstrap's
    # provider construction -- see config/evaluation.production.yaml.
    # Kept as two distinct example config files (not just this one flag) so
    # switching modes is a deliberate, visible choice, never an accident.
    mode: Literal["local", "production"] = "local"
    top_k_values: list[int] = Field(default_factory=lambda: [1, 3, 5])
    similarity_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    local_fixture_csv: str = "data/eval_icd_fixture.csv"
    # Local mode intentionally never touches aegis.config.AppSettings (which
    # unconditionally requires Upstash Vector credentials, even for the demo
    # profile) -- it builds its own SentenceTransformersEmbeddingProvider
    # directly from this field, so it stays credential-free. Production mode
    # ignores this field entirely and uses EMBEDDING_PROVIDER/EMBEDDING_MODEL
    # from settings instead, matching the real application.
    local_embedding_model: str = "BAAI/bge-large-en-v1.5"


class ReasoningEvalConfig(DomainModel):
    """
    Reasoning-evaluation-specific configuration.

    ``reasoning_model`` is informational only -- recorded on the report for
    traceability. Actual provider selection always comes from
    ``AEGIS_PROFILE``/``aegis.config.get_settings()`` via
    ``aegis.api.bootstrap.build_reasoning_provider``, never duplicated here.
    """

    reasoning_model: str | None = None


class EvaluationConfig(DomainModel):
    """Top-level evaluation run configuration."""

    dataset_path: str = "evals/clinical_cases.jsonl"
    output_dir: str = ".artifacts/evaluations"
    retrieval: RetrievalEvalConfig = Field(default_factory=RetrievalEvalConfig)
    reasoning: ReasoningEvalConfig = Field(default_factory=ReasoningEvalConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)


def load_evaluation_config(path: str | Path) -> EvaluationConfig:
    """Parse and validate an ``EvaluationConfig`` from a YAML file."""
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return EvaluationConfig.model_validate(raw)
