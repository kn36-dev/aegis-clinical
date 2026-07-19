import yaml
from pydantic import ValidationError
from pytest import raises

from aegis.evaluation.config import EvaluationConfig, load_evaluation_config
from aegis.evaluation.rate_limiter import RateLimitConfig


class TestEvaluationConfigDefaults:
    def test_defaults_are_ci_safe(self):
        config = EvaluationConfig()

        assert config.retrieval.mode == "local"
        assert config.dataset_path == "evals/clinical_cases.jsonl"
        assert config.output_dir == ".artifacts/evaluations"
        assert isinstance(config.rate_limit, RateLimitConfig)


class TestLoadEvaluationConfig:
    def test_round_trips_from_yaml(self, tmp_path):
        config_path = tmp_path / "evaluation.yaml"
        config_path.write_text(
            yaml.safe_dump(
                {
                    "dataset_path": "evals/clinical_cases.jsonl",
                    "output_dir": ".artifacts/evaluations",
                    "retrieval": {"mode": "production", "top_k_values": [1, 5]},
                    "reasoning": {"reasoning_model": "llama-3.3-70b-versatile"},
                    "rate_limit": {"requests_per_minute": 10},
                }
            )
        )

        config = load_evaluation_config(config_path)

        assert config.retrieval.mode == "production"
        assert config.retrieval.top_k_values == [1, 5]
        assert config.reasoning.reasoning_model == "llama-3.3-70b-versatile"
        assert config.rate_limit.requests_per_minute == 10

    def test_rejects_unknown_top_level_keys(self, tmp_path):
        config_path = tmp_path / "evaluation.yaml"
        config_path.write_text(yaml.safe_dump({"not_a_real_field": True}))

        with raises(ValidationError):
            load_evaluation_config(config_path)

    def test_rejects_invalid_retrieval_mode(self, tmp_path):
        config_path = tmp_path / "evaluation.yaml"
        config_path.write_text(yaml.safe_dump({"retrieval": {"mode": "not-a-mode"}}))

        with raises(ValidationError):
            load_evaluation_config(config_path)

    def test_shipped_example_configs_are_valid(self):
        local_config = load_evaluation_config("config/evaluation.yaml")
        production_config = load_evaluation_config("config/evaluation.production.yaml")

        assert local_config.retrieval.mode == "local"
        assert production_config.retrieval.mode == "production"
