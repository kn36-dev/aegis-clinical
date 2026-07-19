import pytest

from aegis.evaluation.hit_rate import hit_rate_at_k
from aegis.evaluation.metrics import CaseMetrics, compute_case_metrics, mean
from aegis.evaluation.mrr import mrr
from aegis.evaluation.recall import recall_at_k


class TestRecallAtK:
    def test_all_relevant_codes_found_is_full_recall(self):
        assert recall_at_k(["A", "B", "C"], {"A", "B"}, k=3) == 1.0

    def test_partial_overlap_is_fractional_recall(self):
        assert recall_at_k(["A", "X", "Y"], {"A", "B"}, k=3) == 0.5

    def test_relevant_code_outside_k_window_is_not_counted(self):
        assert recall_at_k(["X", "Y", "A"], {"A"}, k=2) == 0.0

    def test_no_relevant_codes_is_zero_not_a_zero_division_error(self):
        assert recall_at_k(["A", "B"], set(), k=2) == 0.0

    def test_no_overlap_is_zero_recall(self):
        assert recall_at_k(["X", "Y"], {"A"}, k=2) == 0.0


class TestHitRateAtK:
    def test_any_relevant_hit_is_full_hit_rate(self):
        assert hit_rate_at_k(["X", "A", "Y"], {"A", "B"}, k=3) == 1.0

    def test_relevant_code_outside_k_window_is_zero(self):
        assert hit_rate_at_k(["X", "Y", "A"], {"A"}, k=2) == 0.0

    def test_no_relevant_codes_is_zero(self):
        assert hit_rate_at_k(["A"], set(), k=1) == 0.0

    def test_multiple_relevant_hits_still_caps_at_one(self):
        assert hit_rate_at_k(["A", "B"], {"A", "B"}, k=2) == 1.0


class TestMRR:
    def test_first_position_hit_is_reciprocal_rank_one(self):
        assert mrr(["A", "X", "Y"], {"A"}) == 1.0

    def test_third_position_hit_is_one_third(self):
        assert mrr(["X", "Y", "A"], {"A"}) == pytest.approx(1 / 3)

    def test_no_hit_is_zero(self):
        assert mrr(["X", "Y"], {"A"}) == 0.0

    def test_first_relevant_hit_wins_when_multiple_relevant_present(self):
        assert mrr(["X", "A", "B"], {"A", "B"}) == 0.5


class TestMean:
    def test_mean_of_values(self):
        assert mean([1.0, 2.0, 3.0]) == 2.0

    def test_mean_of_empty_is_zero(self):
        assert mean([]) == 0.0


class TestComputeCaseMetrics:
    def test_computes_all_configured_k_values_and_mrr(self):
        result = compute_case_metrics(["A", "X", "B"], {"A", "B"}, top_k_values=[1, 2, 3])

        assert isinstance(result, CaseMetrics)
        assert result.recall_at_k == {1: 0.5, 2: 0.5, 3: 1.0}
        assert result.hit_rate_at_k == {1: 1.0, 2: 1.0, 3: 1.0}
        assert result.mrr == 1.0
