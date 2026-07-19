import json
from datetime import datetime, timezone

from aegis.evaluation.config import EvaluationConfig
from aegis.evaluation.metrics import CaseMetrics
from aegis.evaluation.provenance import ProvenanceMetadata
from aegis.evaluation.reasoning_eval import (
    ExpectedCodeAlignment,
    ReasoningCaseResult,
    ReasoningReport,
)
from aegis.evaluation.reports import write_reports
from aegis.evaluation.retrieval_eval import RetrievalCaseResult, RetrievalReport


def make_provenance() -> ProvenanceMetadata:
    return ProvenanceMetadata(
        git_commit="abc123",
        dataset_path="evals/clinical_cases.jsonl",
        dataset_hash="deadbeef",
        config_hash="cafebabe",
        retrieval_backend="local (fixture: data/eval_icd_fixture.csv)",
        model_provider_info="groq/qwen3-32b",
        generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def make_retrieval_report() -> RetrievalReport:
    case_result = RetrievalCaseResult(
        case_id="case_001",
        retrieved_codes=["ME05.1", "DA90.0"],
        relevant_codes={"ME05.1"},
        metrics=CaseMetrics(recall_at_k={1: 1.0, 3: 1.0}, hit_rate_at_k={1: 1.0, 3: 1.0}, mrr=1.0),
    )
    return RetrievalReport(
        case_results=[case_result],
        mean_recall_at_k={1: 1.0, 3: 1.0},
        mean_hit_rate_at_k={1: 1.0, 3: 1.0},
        mean_mrr=1.0,
        zero_hit_case_ids=[],
    )


def make_reasoning_report() -> ReasoningReport:
    case_result = ReasoningCaseResult(
        case_id="case_001",
        schema_valid=True,
        expected_code_alignment=ExpectedCodeAlignment.EXPECTED,
        evidence_grounded=True,
        recommended_codes=["ME05.1"],
        error=None,
    )
    return ReasoningReport(
        case_results=[case_result],
        schema_valid_rate=1.0,
        expected_alignment_rate=1.0,
        acceptable_or_better_alignment_rate=1.0,
        evidence_grounded_rate=1.0,
        misaligned_case_ids=[],
        failed_case_ids=[],
    )


class TestWriteReports:
    def test_writes_all_three_expected_files(self, tmp_path):
        run_dir = tmp_path / "run_20260101T000000Z"

        write_reports(
            run_dir,
            provenance=make_provenance(),
            config=EvaluationConfig(),
            retrieval_report=make_retrieval_report(),
            reasoning_report=make_reasoning_report(),
        )

        assert (run_dir / "retrieval_report.json").exists()
        assert (run_dir / "reasoning_report.json").exists()
        assert (run_dir / "summary.md").exists()

    def test_retrieval_report_json_contains_provenance_and_metrics(self, tmp_path):
        run_dir = tmp_path / "run"
        write_reports(
            run_dir,
            provenance=make_provenance(),
            config=EvaluationConfig(),
            retrieval_report=make_retrieval_report(),
        )

        payload = json.loads((run_dir / "retrieval_report.json").read_text())

        assert payload["provenance"]["git_commit"] == "abc123"
        assert payload["metrics"]["mean_mrr"] == 1.0
        assert payload["case_results"][0]["case_id"] == "case_001"

    def test_omitting_reasoning_report_skips_that_file(self, tmp_path):
        run_dir = tmp_path / "run"
        write_reports(
            run_dir,
            provenance=make_provenance(),
            config=EvaluationConfig(),
            retrieval_report=make_retrieval_report(),
        )

        assert not (run_dir / "reasoning_report.json").exists()
        assert (run_dir / "summary.md").exists()

    def test_summary_markdown_mentions_key_metrics_and_provenance(self, tmp_path):
        run_dir = tmp_path / "run"
        write_reports(
            run_dir,
            provenance=make_provenance(),
            config=EvaluationConfig(),
            retrieval_report=make_retrieval_report(),
            reasoning_report=make_reasoning_report(),
        )

        summary = (run_dir / "summary.md").read_text()

        assert "Retrieval" in summary
        assert "Reasoning" in summary
        assert "abc123" in summary
