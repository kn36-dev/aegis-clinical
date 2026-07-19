"""
Clinical evaluation dataset loading.

Orchestration-layer concern only: parses the JSONL fixture dataset
(``evals/clinical_cases.jsonl``) into typed ``ClinicalCase`` records. The
``expected_codes``/``acceptable_codes`` on each case are the dataset
authors' ground-truth annotations -- this module introduces no clinical,
retrieval, or reasoning logic of its own; those annotations are scored
against real service output elsewhere in this package.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ClinicalCase(BaseModel):
    """One ground-truth-annotated case in the evaluation dataset."""

    id: str = Field(min_length=1)
    note: str = Field(min_length=1)
    expected_codes: list[str] = Field(min_length=1)
    acceptable_codes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


def load_clinical_cases(path: str | Path) -> list[ClinicalCase]:
    """
    Parse a JSONL dataset file into ``ClinicalCase`` records.

    One JSON object per non-blank line, matching ``evals/clinical_cases.jsonl``.
    Raises ``ValueError`` (with the offending line number) on malformed JSON
    or a case that fails schema validation, rather than silently skipping it.
    """
    dataset_path = Path(path)
    cases: list[ClinicalCase] = []

    with dataset_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as error:
                raise ValueError(f"{dataset_path}:{line_number}: invalid JSON: {error}") from error
            cases.append(ClinicalCase.model_validate(payload))

    return cases
