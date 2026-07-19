"""Command-line entry point for the AEGIS evaluation framework (``aegis-eval``)."""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from aegis.evaluation import runner
from aegis.evaluation.config import EvaluationConfig, load_evaluation_config
from aegis.evaluation.provenance import build_provenance
from aegis.evaluation.reports import write_reports

if TYPE_CHECKING:
    from collections.abc import Sequence

    from aegis.evaluation.reasoning_eval import ReasoningReport
    from aegis.evaluation.retrieval_eval import RetrievalReport

logger = logging.getLogger("aegis.evaluation.cli")

DEFAULT_CONFIG_PATH = "config/evaluation.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aegis-eval")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("retrieval", "reasoning", "all"):
        subparser = subparsers.add_parser(name, help=f"Run {name} evaluation")
        subparser.add_argument(
            "--config", type=str, default=DEFAULT_CONFIG_PATH, help="Path to evaluation YAML config"
        )
        subparser.add_argument(
            "--dataset", type=str, default=None, help="Override config.dataset_path"
        )
        subparser.add_argument(
            "--output-dir", type=str, default=None, help="Override config.output_dir"
        )

    return parser


def _apply_overrides(config: EvaluationConfig, args: argparse.Namespace) -> EvaluationConfig:
    updates: dict[str, str] = {}
    if args.dataset:
        updates["dataset_path"] = args.dataset
    if args.output_dir:
        updates["output_dir"] = args.output_dir
    return config.model_copy(update=updates) if updates else config


def _timestamped_run_dir(output_dir: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path(output_dir) / f"run_{timestamp}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    config = _apply_overrides(load_evaluation_config(args.config), args)

    retrieval_report: RetrievalReport | None = None
    reasoning_report: ReasoningReport | None = None
    backend_label = "unknown"
    model_provider_info = "n/a"

    if args.command in ("retrieval", "all"):
        retrieval_report, backend_label = runner.run_retrieval_evaluation(config)
        logger.info("Retrieval evaluation complete: mean MRR=%.3f", retrieval_report.mean_mrr)

    if args.command in ("reasoning", "all"):
        reasoning_report, backend_label, model_provider_info = asyncio.run(
            runner.run_reasoning_evaluation(config)
        )
        logger.info(
            "Reasoning evaluation complete: expected-alignment rate=%.3f",
            reasoning_report.expected_alignment_rate,
        )

    provenance = build_provenance(
        dataset_path=config.dataset_path,
        config_path=args.config,
        retrieval_backend=backend_label,
        model_provider_info=model_provider_info,
    )

    run_dir = write_reports(
        _timestamped_run_dir(config.output_dir),
        provenance=provenance,
        config=config,
        retrieval_report=retrieval_report,
        reasoning_report=reasoning_report,
    )

    print(f"Evaluation report written to {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
