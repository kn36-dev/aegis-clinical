import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsConfigDict

from aegis.config import AppSettings


class AppSettingsForTests(AppSettings):
    """
    Test-only settings that disable .env loading so tests are isolated.
    """

    model_config = SettingsConfigDict(
        env_file=None,
        extra="ignore",
    )


def valid_settings_kwargs(profile: str = "production") -> dict:
    return {
        "AEGIS_PROFILE": profile,
        "GROQ_API_KEY": "test-groq-key",
        "UPSTASH_VECTOR_REST_URL": "https://vector.example.com",
        "UPSTASH_VECTOR_REST_TOKEN": "vector-token",
        "UPSTASH_REDIS_REST_URL": "https://redis.example.com",
        "UPSTASH_REDIS_REST_TOKEN": "redis-token",
        "LLM_PROVIDER": "groq",
        "LLM_MODEL": "test-model",
        "EMBEDDING_PROVIDER": "sentence_transformers",
        "EMBEDDING_MODEL": "BAAI/bge-large-en-v1.5",
        "EMBEDDING_DIMENSIONS": 1024,
    }


def test_app_settings_load_correctly():
    settings = AppSettingsForTests(**valid_settings_kwargs())

    assert settings.AEGIS_PROFILE == "production"

    assert settings.LLM_PROVIDER == "groq"
    assert settings.LLM_MODEL == "test-model"

    assert settings.GROQ_API_KEY is not None
    assert settings.GROQ_API_KEY.get_secret_value() == "test-groq-key"

    assert str(settings.UPSTASH_VECTOR_REST_URL) == "https://vector.example.com/"

    assert settings.UPSTASH_VECTOR_REST_TOKEN.get_secret_value() == "vector-token"

    assert str(settings.UPSTASH_REDIS_REST_URL) == "https://redis.example.com/"

    assert settings.UPSTASH_REDIS_REST_TOKEN is not None
    assert settings.UPSTASH_REDIS_REST_TOKEN.get_secret_value() == "redis-token"


@pytest.mark.parametrize(
    "missing_field",
    [
        "UPSTASH_VECTOR_REST_URL",
        "UPSTASH_VECTOR_REST_TOKEN",
        "EMBEDDING_PROVIDER",
        "EMBEDDING_MODEL",
        "EMBEDDING_DIMENSIONS",
    ],
)
def test_universal_settings_are_required(missing_field, monkeypatch):
    """
    Vector infrastructure and embedding configuration are required
    for every profile, including demo.

    Demo only replaces reasoning/cache/content collaborators; it still
    performs real embedding + Upstash Vector retrieval.
    """

    kwargs = valid_settings_kwargs(profile="demo")

    kwargs.pop(missing_field)

    monkeypatch.delenv(missing_field, raising=False)

    with pytest.raises(ValidationError):
        AppSettingsForTests(**kwargs)


@pytest.mark.parametrize(
    "profile",
    [
        "production",
        "integration",
    ],
)
@pytest.mark.parametrize(
    "missing_field",
    [
        "GROQ_API_KEY",
        "UPSTASH_REDIS_REST_URL",
        "UPSTASH_REDIS_REST_TOKEN",
    ],
)
def test_real_runtime_profiles_require_external_credentials(
    profile,
    missing_field,
    monkeypatch,
):
    """
    Production and integration profiles use real CrewAI reasoning and
    Redis-backed cache, therefore these credentials are mandatory.
    """

    kwargs = valid_settings_kwargs(profile=profile)

    kwargs.pop(missing_field)

    monkeypatch.delenv(missing_field, raising=False)

    with pytest.raises(ValidationError):
        AppSettingsForTests(**kwargs)


@pytest.mark.parametrize(
    "missing_field",
    [
        "GROQ_API_KEY",
        "UPSTASH_REDIS_REST_URL",
        "UPSTASH_REDIS_REST_TOKEN",
    ],
)
def test_demo_profile_does_not_require_real_runtime_credentials(
    missing_field,
    monkeypatch,
):
    """
    Demo profile intentionally avoids external reasoning/cache
    dependencies by using deterministic in-memory collaborators.
    """

    kwargs = valid_settings_kwargs(profile="demo")

    kwargs.pop(missing_field)

    monkeypatch.delenv(missing_field, raising=False)

    settings = AppSettingsForTests(**kwargs)

    assert settings.AEGIS_PROFILE == "demo"
