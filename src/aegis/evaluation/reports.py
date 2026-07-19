"""
Evaluation report writing.

Serializes a completed retrieval and/or reasoning evaluation run --
along with its ``ProvenanceMetadata`` and the ``EvaluationConfig`` that
produced it -- into a timestamped run directory:

    <output_dir>/run_<timestamp>/
        retrieval_report.json
        reasoning_report.json
        summary.md

Pure orchestration/serialization -- no metric computation happens here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aegis.evaluation.config import EvaluationConfig
    from aegis.evaluation.provenance import ProvenanceMetadata
    from aegis.evaluation.reasoning_eval import ReasoningReport
    from aegis.evaluation.retrieval_eval import RetrievalReport


def _retrieval_report_dict(
    report: RetrievalReport, provenance: ProvenanceMetadata, config: EvaluationConfig
) -> dict[str, Any]:
    return {
        "provenance": provenance.model_dump(mode="json"),
        "config_used": config.model_dump(mode="json"),
        "metrics": {
            "mean_recall_at_k": report.mean_recall_at_k,
            "mean_hit_rate_at_k": report.mean_hit_rate_at_k,
            "mean_mrr": report.mean_mrr,
        },
        "failures": {"zero_hit_case_ids": report.zero_hit_case_ids},
        "execution_summary": {"case_count": len(report.case_results)},
        "case_results": [
            {
                "case_id": result.case_id,
                "retrieved_codes": result.retrieved_codes,
                "relevant_codes": sorted(result.relevant_codes),
                "recall_at_k": result.metrics.recall_at_k,
                "hit_rate_at_k": result.metrics.hit_rate_at_k,
                "mrr": result.metrics.mrr,
            }
            for result in report.case_results
        ],
    }


def _reasoning_report_dict(
    report: ReasoningReport, provenance: ProvenanceMetadata, config: EvaluationConfig
) -> dict[str, Any]:
    return {
        "provenance": provenance.model_dump(mode="json"),
        "config_used": config.model_dump(mode="json"),
        "metrics": {
            "schema_valid_rate": report.schema_valid_rate,
            "expected_alignment_rate": report.expected_alignment_rate,
            "acceptable_or_better_alignment_rate": report.acceptable_or_better_alignment_rate,
            "evidence_grounded_rate": report.evidence_grounded_rate,
        },
        "failures": {
            "misaligned_case_ids": report.misaligned_case_ids,
            "failed_case_ids": report.failed_case_ids,
        },
        "execution_summary": {"case_count": len(report.case_results)},
        "case_results": [
            {
                "case_id": result.case_id,
                "schema_valid": result.schema_valid,
                "expected_code_alignment": (
                    result.expected_code_alignment.value
                    if result.expected_code_alignment is not None
                    else None
                ),
                "evidence_grounded": result.evidence_grounded,
                "recommended_codes": result.recommended_codes,
                "error": result.error,
            }
            for result in report.case_results
        ],
    }


def _render_summary_markdown(
    retrieval_report: RetrievalReport | None,
    reasoning_report: ReasoningReport | None,
    provenance: ProvenanceMetadata,
) -> str:
    lines = [
        "# AEGIS Evaluation Run Summary",
        "",
        f"- Generated at: {provenance.generated_at.isoformat()}",
        f"- Git commit: {provenance.git_commit or 'unknown'}",
        f"- Dataset: {provenance.dataset_path} (sha256 {provenance.dataset_hash[:12]}...)",
        f"- Retrieval backend: {provenance.retrieval_backend}",
        f"- Model/provider: {provenance.model_provider_info}",
        "",
    ]

    if retrieval_report is not None:
        lines += ["## Retrieval", "", "| K | Recall@K | Hit Rate@K |", "| --- | --- | --- |"]
        for k in sorted(retrieval_report.mean_recall_at_k):
            lines.append(
                f"| {k} | {retrieval_report.mean_recall_at_k[k]:.3f} "
                f"| {retrieval_report.mean_hit_rate_at_k[k]:.3f} |"
            )
        lines += [
            "",
            f"MRR: {retrieval_report.mean_mrr:.3f}",
            "",
            f"Zero-hit cases: {retrieval_report.zero_hit_case_ids or 'none'}",
            "",
        ]

    if reasoning_report is not None:
        lines += [
            "## Reasoning",
            "",
            f"- Schema-valid rate: {reasoning_report.schema_valid_rate:.3f}",
            f"- Expected-code alignment rate: {reasoning_report.expected_alignment_rate:.3f}",
            "- Acceptable-or-better alignment rate: "
            f"{reasoning_report.acceptable_or_better_alignment_rate:.3f}",
            f"- Evidence-grounded rate: {reasoning_report.evidence_grounded_rate:.3f}",
            f"- Misaligned cases: {reasoning_report.misaligned_case_ids or 'none'}",
            f"- Failed cases: {reasoning_report.failed_case_ids or 'none'}",
            "",
        ]

    return "\n".join(lines)


def write_reports(
    run_dir: str | Path,
    *,
    provenance: ProvenanceMetadata,
    config: EvaluationConfig,
    retrieval_report: RetrievalReport | None = None,
    reasoning_report: ReasoningReport | None = None,
) -> Path:
    """
    Write ``retrieval_report.json``/``reasoning_report.json`` (whichever
    reports are supplied) and ``summary.md`` into ``run_dir``, creating it
    if necessary. Returns the run directory path.
    """
    output_dir = Path(run_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if retrieval_report is not None:
        (output_dir / "retrieval_report.json").write_text(
            json.dumps(_retrieval_report_dict(retrieval_report, provenance, config), indent=2),
            encoding="utf-8",
        )

    if reasoning_report is not None:
        (output_dir / "reasoning_report.json").write_text(
            json.dumps(_reasoning_report_dict(reasoning_report, provenance, config), indent=2),
            encoding="utf-8",
        )

    (output_dir / "summary.md").write_text(
        _render_summary_markdown(retrieval_report, reasoning_report, provenance),
        encoding="utf-8",
    )

    return output_dir
