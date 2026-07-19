import subprocess

from aegis.evaluation.provenance import _current_git_commit, build_provenance


def _write(tmp_path, name: str, content: str):
    path = tmp_path / name
    path.write_text(content)
    return path


class TestBuildProvenance:
    def test_hash_is_deterministic_for_identical_file_contents(self, tmp_path):
        dataset_path = _write(tmp_path, "cases.jsonl", '{"id": "case_001"}\n')
        config_path = _write(tmp_path, "config.yaml", "dataset_path: x\n")

        first = build_provenance(
            dataset_path=dataset_path,
            config_path=config_path,
            retrieval_backend="local",
            model_provider_info="n/a",
        )
        second = build_provenance(
            dataset_path=dataset_path,
            config_path=config_path,
            retrieval_backend="local",
            model_provider_info="n/a",
        )

        assert first.dataset_hash == second.dataset_hash
        assert first.config_hash == second.config_hash

    def test_hash_changes_when_dataset_contents_change(self, tmp_path):
        dataset_path = _write(tmp_path, "cases.jsonl", '{"id": "case_001"}\n')
        config_path = _write(tmp_path, "config.yaml", "dataset_path: x\n")

        before = build_provenance(
            dataset_path=dataset_path,
            config_path=config_path,
            retrieval_backend="local",
            model_provider_info="n/a",
        )
        dataset_path.write_text('{"id": "case_002"}\n')
        after = build_provenance(
            dataset_path=dataset_path,
            config_path=config_path,
            retrieval_backend="local",
            model_provider_info="n/a",
        )

        assert before.dataset_hash != after.dataset_hash

    def test_carries_through_backend_and_model_labels(self, tmp_path):
        dataset_path = _write(tmp_path, "cases.jsonl", "{}\n")
        config_path = _write(tmp_path, "config.yaml", "a: 1\n")

        provenance = build_provenance(
            dataset_path=dataset_path,
            config_path=config_path,
            retrieval_backend="local (fixture: x.csv)",
            model_provider_info="groq/qwen3-32b",
        )

        assert provenance.retrieval_backend == "local (fixture: x.csv)"
        assert provenance.model_provider_info == "groq/qwen3-32b"


class TestCurrentGitCommit:
    def test_returns_none_when_git_lookup_fails(self, monkeypatch):
        def _raise(*args, **kwargs):
            raise FileNotFoundError("git not found")

        monkeypatch.setattr(subprocess, "run", _raise)

        assert _current_git_commit() is None
