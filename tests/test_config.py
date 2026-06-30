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


def valid_settings_kwargs() -> dict:
    return {
        "GROQ_API_KEY": "test-groq-key",
        "UPSTASH_VECTOR_REST_URL": "https://vector.example.com",
        "UPSTASH_VECTOR_REST_TOKEN": "vector-token",
        "UPSTASH_REDIS_REST_URL": "https://redis.example.com",
        "UPSTASH_REDIS_REST_TOKEN": "redis-token",
        "LLM_PROVIDER": "groq",
        "LLM_MODEL": "test-model",
    }


def test_app_settings_load_correctly():
    settings = AppSettingsForTests(**valid_settings_kwargs())

    assert settings.LLM_PROVIDER == "groq"
    assert settings.LLM_MODEL == "test-model"

    assert settings.GROQ_API_KEY.get_secret_value() == "test-groq-key"

    assert str(settings.UPSTASH_VECTOR_REST_URL) == "https://vector.example.com/"

    assert settings.UPSTASH_VECTOR_REST_TOKEN.get_secret_value() == "vector-token"

    assert str(settings.UPSTASH_REDIS_REST_URL) == "https://redis.example.com/"

    assert settings.UPSTASH_REDIS_REST_TOKEN.get_secret_value() == "redis-token"


@pytest.mark.parametrize(
    "missing_field",
    [
        "GROQ_API_KEY",
        "UPSTASH_VECTOR_REST_URL",
        "UPSTASH_VECTOR_REST_TOKEN",
        "UPSTASH_REDIS_REST_URL",
        "UPSTASH_REDIS_REST_TOKEN",
    ],
)
def test_missing_required_settings_raise_validation_error(
    missing_field,
):
    kwargs = valid_settings_kwargs()

    kwargs.pop(missing_field)

    with pytest.raises(ValidationError):
        AppSettingsForTests(**kwargs)
