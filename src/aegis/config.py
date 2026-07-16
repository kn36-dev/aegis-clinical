# src/aegis/config.py
from functools import lru_cache
from typing import TYPE_CHECKING, Any, cast

from pydantic import Field, HttpUrl, SecretStr, ValidationError

# Move the import here
if TYPE_CHECKING:
    from pydantic_core import InitErrorDetails
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """
    Centralized runtime configuration for the Aegis platform.

    Configuration is validated once during application startup,
    causing the application to fail fast if any required values
    are missing or malformed.
    """

    ENVIRONMENT: str = Field(default="development")

    LLM_PROVIDER: str = Field(default="groq")
    LLM_MODEL: str = Field(default="qwen/qwen3-32b")
    GROQ_API_KEY: SecretStr = Field(default=...)
    REASONING_TEMPERATURE: float = Field(default=0.0, ge=0.0)

    UPSTASH_VECTOR_REST_URL: HttpUrl = Field(default=...)
    UPSTASH_VECTOR_REST_TOKEN: SecretStr = Field(default=...)

    UPSTASH_REDIS_REST_URL: HttpUrl = Field(default=...)
    UPSTASH_REDIS_REST_TOKEN: SecretStr = Field(default=...)
    CACHE_TTL_SECONDS: int = Field(default=60 * 60 * 24 * 30, gt=0)

    # Embedding <-> vector-index compatibility boundary. There is
    # intentionally no default: an operator must state all three
    # explicitly, matching whatever actually populated the target
    # Upstash Vector index, rather than the application silently
    # assuming a provider. See EmbeddingConfiguration in api/bootstrap.py.
    EMBEDDING_PROVIDER: str = Field(default=...)
    EMBEDDING_MODEL: str = Field(default=...)
    EMBEDDING_DIMENSIONS: int = Field(default=..., gt=0)
    # Only required when EMBEDDING_PROVIDER == "openai" -- checked below.
    OPENAI_API_KEY: SecretStr | None = Field(default=None)

    RETRIEVAL_TOP_K: int = Field(default=5, gt=0)
    RETRIEVAL_SIMILARITY_THRESHOLD: float | None = Field(default=None)

    # Local SQLite paths defined in your architecture map
    CLINICAL_DB_PATH: str = "data/clinical_registry.db"
    GRAPH_CHECKPOINT_DB_PATH: str = "data/graph_checkpoints.db"

    # Standard configuration for local development portfolios
    model_config = SettingsConfigDict(
        env_file=".env",  # Reads from local uncommitted file
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **values: Any) -> None:
        super().__init__(**values)

        missing_fields: list[str] = []

        if not self.GROQ_API_KEY or not self.GROQ_API_KEY.get_secret_value():
            missing_fields.append("GROQ_API_KEY")

        if not self.UPSTASH_VECTOR_REST_URL:
            missing_fields.append("UPSTASH_VECTOR_REST_URL")

        if (
            not self.UPSTASH_VECTOR_REST_TOKEN
            or not self.UPSTASH_VECTOR_REST_TOKEN.get_secret_value()
        ):
            missing_fields.append("UPSTASH_VECTOR_REST_TOKEN")

        if not self.UPSTASH_REDIS_REST_URL:
            missing_fields.append("UPSTASH_REDIS_REST_URL")

        if (
            not self.UPSTASH_REDIS_REST_TOKEN
            or not self.UPSTASH_REDIS_REST_TOKEN.get_secret_value()
        ):
            missing_fields.append("UPSTASH_REDIS_REST_TOKEN")

        if not self.EMBEDDING_PROVIDER:
            missing_fields.append("EMBEDDING_PROVIDER")

        if not self.EMBEDDING_MODEL:
            missing_fields.append("EMBEDDING_MODEL")

        if not self.EMBEDDING_DIMENSIONS:
            missing_fields.append("EMBEDDING_DIMENSIONS")

        if self.EMBEDDING_PROVIDER == "openai" and (
            not self.OPENAI_API_KEY or not self.OPENAI_API_KEY.get_secret_value()
        ):
            missing_fields.append("OPENAI_API_KEY")

        if missing_fields:
            line_errors = cast(
                "list[InitErrorDetails]",
                [
                    {
                        "type": "missing",
                        "loc": (field_name,),
                        "msg": "Field required",
                        "input": None,
                    }
                    for field_name in missing_fields
                ],
            )
            raise ValidationError.from_exception_data(title="AppSettings", line_errors=line_errors)


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
