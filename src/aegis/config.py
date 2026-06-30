# src/aegis/config.py
from functools import lru_cache
from typing import TYPE_CHECKING, cast

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

    UPSTASH_VECTOR_REST_URL: HttpUrl = Field(default=...)
    UPSTASH_VECTOR_REST_TOKEN: SecretStr = Field(default=...)

    UPSTASH_REDIS_REST_URL: HttpUrl = Field(default=...)
    UPSTASH_REDIS_REST_TOKEN: SecretStr = Field(default=...)

    # Local SQLite paths defined in your architecture map
    CLINICAL_DB_PATH: str = "data/clinical_registry.db"
    GRAPH_CHECKPOINT_DB_PATH: str = "data/graph_checkpoints.db"

    # Standard configuration for local development portfolios
    model_config = SettingsConfigDict(
        env_file=".env",  # Reads from local uncommitted file
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **values):
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
