# Application Bootstrap Layer: constructing infrastructure adapters
# from AppSettings and enforcing the embedding/vector-index
# compatibility boundary before the application accepts traffic.
from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from aegis.api.bootstrap import (
    EmbeddingCompatibilityError,
    EmbeddingConfiguration,
    build_cache_repository,
    build_embedding_provider,
    build_infrastructure,
    open_clinical_connection,
    validate_embedding_compatibility,
)
from aegis.embeddings.openai import OpenAIEmbeddingProvider
from aegis.embeddings.sentence_transformers import SentenceTransformersEmbeddingProvider
from aegis.infrastructure.memory.clinical_decision_cache_repository import (
    FakeClinicalDecisionCacheRepository,
)
from aegis.infrastructure.upstash.clinical_decision_cache_repository import (
    UpstashClinicalDecisionCacheRepository,
)
from tests.application.fakes import FakeEmbeddingProvider

if TYPE_CHECKING:
    from pathlib import Path


class _SettingsStub:
    def __init__(self, **overrides: object) -> None:
        self.OPENAI_API_KEY = None
        self.AEGIS_PROFILE = "demo"
        self.__dict__.update(overrides)


class TestBuildEmbeddingProvider:
    def test_openai_provider_is_constructed_from_config_and_settings(self) -> None:
        config = EmbeddingConfiguration(
            provider="openai", model="text-embedding-3-small", dimensions=1536
        )
        settings = _SettingsStub(OPENAI_API_KEY=MagicMock(get_secret_value=lambda: "sk-test"))

        provider = build_embedding_provider(config, settings)  # type: ignore[arg-type]

        assert isinstance(provider, OpenAIEmbeddingProvider)
        assert provider.model == "text-embedding-3-small"

    def test_openai_provider_without_api_key_raises(self) -> None:
        config = EmbeddingConfiguration(
            provider="openai", model="text-embedding-3-small", dimensions=1536
        )
        settings = _SettingsStub(OPENAI_API_KEY=None)

        with pytest.raises(EmbeddingCompatibilityError, match="OPENAI_API_KEY"):
            build_embedding_provider(config, settings)  # type: ignore[arg-type]

    def test_sentence_transformers_provider_is_constructed_from_config(self) -> None:
        config = EmbeddingConfiguration(
            provider="sentence_transformers", model="BAAI/bge-large-en-v1.5", dimensions=1024
        )
        settings = _SettingsStub()

        provider = build_embedding_provider(config, settings)  # type: ignore[arg-type]

        assert isinstance(provider, SentenceTransformersEmbeddingProvider)

    def test_unknown_provider_raises(self) -> None:
        config = EmbeddingConfiguration(provider="pinecone-embed", model="whatever", dimensions=10)
        settings = _SettingsStub()

        with pytest.raises(EmbeddingCompatibilityError, match="Unknown EMBEDDING_PROVIDER"):
            build_embedding_provider(config, settings)  # type: ignore[arg-type]


class TestValidateEmbeddingCompatibility:
    def test_passes_when_provider_output_matches_configured_dimensions(self) -> None:
        config = EmbeddingConfiguration(provider="fake", model="fake-model", dimensions=3)
        embedding_provider = FakeEmbeddingProvider(vector=[0.1, 0.2, 0.3])
        vector_query_provider = object()  # no get_index_dimension -- introspection is optional

        validate_embedding_compatibility(config, embedding_provider, vector_query_provider)  # type: ignore[arg-type]

    def test_raises_when_provider_output_dimension_mismatches_config(self) -> None:
        config = EmbeddingConfiguration(provider="fake", model="fake-model", dimensions=1536)
        embedding_provider = FakeEmbeddingProvider(vector=[0.1, 0.2, 0.3])
        vector_query_provider = object()

        with pytest.raises(EmbeddingCompatibilityError, match="EMBEDDING_DIMENSIONS"):
            validate_embedding_compatibility(config, embedding_provider, vector_query_provider)  # type: ignore[arg-type]

    def test_raises_when_live_index_dimension_mismatches_config(self) -> None:
        config = EmbeddingConfiguration(provider="fake", model="fake-model", dimensions=3)
        embedding_provider = FakeEmbeddingProvider(vector=[0.1, 0.2, 0.3])
        vector_query_provider = MagicMock(get_index_dimension=lambda: 1024)

        with pytest.raises(EmbeddingCompatibilityError, match="live Upstash index"):
            validate_embedding_compatibility(config, embedding_provider, vector_query_provider)  # type: ignore[arg-type]

    def test_passes_when_live_index_dimension_matches_config(self) -> None:
        config = EmbeddingConfiguration(provider="fake", model="fake-model", dimensions=3)
        embedding_provider = FakeEmbeddingProvider(vector=[0.1, 0.2, 0.3])
        vector_query_provider = MagicMock(get_index_dimension=lambda: 3)

        validate_embedding_compatibility(config, embedding_provider, vector_query_provider)  # type: ignore[arg-type]


class TestOpenClinicalConnection:
    def test_runs_migrations_and_returns_a_working_connection(self, tmp_path: Path) -> None:
        db_path = tmp_path / "clinical_registry.db"
        settings = _SettingsStub(CLINICAL_DB_PATH=str(db_path))

        connection = open_clinical_connection(settings)  # type: ignore[arg-type]
        try:
            assert isinstance(connection, sqlite3.Connection)
            row = connection.execute("PRAGMA foreign_keys;").fetchone()
            assert row[0] == 1
            connection.execute("SELECT 1 FROM patient_case LIMIT 1;")
        finally:
            connection.close()

    def test_is_idempotent_across_repeated_calls(self, tmp_path: Path) -> None:
        db_path = tmp_path / "clinical_registry.db"
        settings = _SettingsStub(CLINICAL_DB_PATH=str(db_path))

        first = open_clinical_connection(settings)  # type: ignore[arg-type]
        first.close()

        second = open_clinical_connection(settings)  # type: ignore[arg-type]
        try:
            second.execute("SELECT 1 FROM patient_case LIMIT 1;")
        finally:
            second.close()


class TestBuildCacheRepository:
    def test_demo_profile_uses_fake_repository(self) -> None:
        settings = _SettingsStub(AEGIS_PROFILE="demo")

        repository = build_cache_repository(settings)  # type: ignore[arg-type]

        assert isinstance(repository, FakeClinicalDecisionCacheRepository)

    @patch("aegis.infrastructure.upstash.clinical_decision_cache_repository.Redis")
    def test_production_profile_namespaces_keys_by_profile_name_by_default(
        self, mock_redis_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_redis_cls.return_value = mock_client
        mock_client.get.return_value = None
        settings = _SettingsStub(
            AEGIS_PROFILE="production",
            UPSTASH_REDIS_REST_URL="https://example.upstash.io",
            UPSTASH_REDIS_REST_TOKEN=MagicMock(get_secret_value=lambda: "token"),
            CACHE_TTL_SECONDS=60,
            REDIS_CACHE_NAMESPACE=None,
        )

        repository = build_cache_repository(settings)  # type: ignore[arg-type]
        assert isinstance(repository, UpstashClinicalDecisionCacheRepository)
        repository.get("shared-cache-key")

        mock_client.get.assert_called_once_with("aegis:production:shared-cache-key")

    @patch("aegis.infrastructure.upstash.clinical_decision_cache_repository.Redis")
    def test_integration_profile_namespaces_keys_by_profile_name_by_default(
        self, mock_redis_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_redis_cls.return_value = mock_client
        mock_client.get.return_value = None
        settings = _SettingsStub(
            AEGIS_PROFILE="integration",
            UPSTASH_REDIS_REST_URL="https://example.upstash.io",
            UPSTASH_REDIS_REST_TOKEN=MagicMock(get_secret_value=lambda: "token"),
            CACHE_TTL_SECONDS=60,
            REDIS_CACHE_NAMESPACE=None,
        )

        repository = build_cache_repository(settings)  # type: ignore[arg-type]
        repository.get("shared-cache-key")

        mock_client.get.assert_called_once_with("aegis:integration:shared-cache-key")

    @patch("aegis.infrastructure.upstash.clinical_decision_cache_repository.Redis")
    def test_production_and_integration_defaults_do_not_collide_on_the_same_cache_key(
        self, mock_redis_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_redis_cls.return_value = mock_client
        mock_client.get.return_value = None
        production_settings = _SettingsStub(
            AEGIS_PROFILE="production",
            UPSTASH_REDIS_REST_URL="https://example.upstash.io",
            UPSTASH_REDIS_REST_TOKEN=MagicMock(get_secret_value=lambda: "token"),
            CACHE_TTL_SECONDS=60,
            REDIS_CACHE_NAMESPACE=None,
        )
        integration_settings = _SettingsStub(
            AEGIS_PROFILE="integration",
            UPSTASH_REDIS_REST_URL="https://example.upstash.io",
            UPSTASH_REDIS_REST_TOKEN=MagicMock(get_secret_value=lambda: "token"),
            CACHE_TTL_SECONDS=60,
            REDIS_CACHE_NAMESPACE=None,
        )

        build_cache_repository(production_settings).get("shared-cache-key")  # type: ignore[arg-type]
        build_cache_repository(integration_settings).get("shared-cache-key")  # type: ignore[arg-type]

        production_key, integration_key = (call.args[0] for call in mock_client.get.call_args_list)
        assert production_key != integration_key

    @patch("aegis.infrastructure.upstash.clinical_decision_cache_repository.Redis")
    def test_explicit_namespace_overrides_the_profile_derived_default(
        self, mock_redis_cls: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_redis_cls.return_value = mock_client
        mock_client.get.return_value = None
        settings = _SettingsStub(
            AEGIS_PROFILE="integration",
            UPSTASH_REDIS_REST_URL="https://example.upstash.io",
            UPSTASH_REDIS_REST_TOKEN=MagicMock(get_secret_value=lambda: "token"),
            CACHE_TTL_SECONDS=60,
            REDIS_CACHE_NAMESPACE="integration-suite-2",
        )

        repository = build_cache_repository(settings)  # type: ignore[arg-type]
        repository.get("shared-cache-key")

        mock_client.get.assert_called_once_with("aegis:integration-suite-2:shared-cache-key")


class TestBuildInfrastructure:
    def test_raises_before_constructing_the_container_on_dimension_mismatch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from aegis.api import bootstrap as bootstrap_module

        db_path = tmp_path / "clinical_registry.db"
        settings = _SettingsStub(
            EMBEDDING_PROVIDER="fake",
            EMBEDDING_MODEL="fake-model",
            EMBEDDING_DIMENSIONS=1536,
            CLINICAL_DB_PATH=str(db_path),
        )
        monkeypatch.setattr(
            bootstrap_module,
            "build_embedding_provider",
            lambda config, settings: FakeEmbeddingProvider(vector=[0.1, 0.2, 0.3]),
        )
        monkeypatch.setattr(
            bootstrap_module, "build_vector_query_provider", lambda settings: object()
        )
        connection = open_clinical_connection(
            _SettingsStub(CLINICAL_DB_PATH=str(db_path))  # type: ignore[arg-type]
        )

        try:
            with pytest.raises(EmbeddingCompatibilityError):
                build_infrastructure(settings, connection)  # type: ignore[arg-type]
        finally:
            connection.close()
