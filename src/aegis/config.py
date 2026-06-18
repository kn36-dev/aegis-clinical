# src/aegis/config.py
from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """
    Defines runtime type boundaries for the Aegis engine.
    Fails fast at application boot if required variables are absent.
    """

    ENVIRONMENT: str = Field(default="development")
    GROQ_API_KEY: SecretStr  # Enforces value presence and masks logging output
    UPSTASH_VECTOR_REST_URL: HttpUrl
    UPSTASH_VECTOR_REST_TOKEN: SecretStr

    # Local SQLite paths defined in your architecture map
    CLINICAL_DB_PATH: str = "data/clinical_registry.db"
    GRAPH_CHECKPOINT_DB_PATH: str = "data/graph_checkpoints.db"

    # Standard configuration for local development portfolios
    model_config = SettingsConfigDict(
        env_file=".env",  # Reads from local uncommitted file
        env_file_encoding="utf-8",
        extra="ignore",
    )


# NOTE FOR PRODUCTION DEPLOYMENT:
# For this portfolio context, configuration is pulled from a localized, git-ignored .env file.
# In a medical-grade enterprise architecture, model_config's `env_file` would be set to None,
# forcing the application to intercept secrets directly from a centralized cloud secret runner
# (e.g., Infisical CLI wrapper or AWS Secrets Manager sidecar) to preserve strict cluster isolation.
settings = AppSettings()
