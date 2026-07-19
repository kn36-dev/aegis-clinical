# src/aegis/config.py
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Literal, cast

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

    # Selects which collaborators the composition root (api/bootstrap.py)
    # assembles for the cache, reasoning, content-repository, and (for
    # "demo-local" only) vector-retrieval boundaries -- see CLAUDE.md's
    # demo-profile design. "production" and "integration" both require
    # GROQ_API_KEY and the Upstash Redis credentials below; "demo" and
    # "demo-local" do not, since those three collaborators are replaced
    # with deterministic in-memory adapters. Upstash Vector and the
    # embedding provider are unconditionally required in "production",
    # "demo", and "integration" -- all three keep real semantic
    # retrieval against a live Upstash Vector index. "demo-local" is the
    # one profile that also replaces retrieval itself: it compiles the
    # real ICD-11 taxonomy into a local, file-backed vector index (see
    # aegis.indexing.local_compiler) so a reviewer needs no Upstash
    # Vector credentials at all. "integration" runs the same real
    # collaborators as "production" (see api/bootstrap.py) and exists
    # so scripts/integration_e2e.py can verify external infrastructure
    # wiring under its own profile name rather than overloading
    # "production".
    AEGIS_PROFILE: Literal["production", "demo", "demo-local", "integration"] = Field(
        default="production"
    )

    LLM_PROVIDER: str = Field(default="groq")
    LLM_MODEL: str = Field(default="llama-3.3-70b-versatile")
    # Required only when AEGIS_PROFILE == "production" -- checked below.
    GROQ_API_KEY: SecretStr | None = Field(default=None)
    REASONING_TEMPERATURE: float = Field(default=0.0, ge=0.0)

    # Required in every profile except "demo-local", which serves
    # retrieval entirely from a compiled local vector index and never
    # queries a live Upstash Vector index -- checked below.
    UPSTASH_VECTOR_REST_URL: HttpUrl | None = Field(default=None)
    UPSTASH_VECTOR_REST_TOKEN: SecretStr | None = Field(default=None)

    # Required only when AEGIS_PROFILE == "production" -- checked below.
    UPSTASH_REDIS_REST_URL: HttpUrl | None = Field(default=None)
    UPSTASH_REDIS_REST_TOKEN: SecretStr | None = Field(default=None)
    CACHE_TTL_SECONDS: int = Field(default=60 * 60 * 24 * 30, gt=0)
    # Redis key namespace for the cache adapter -- keeps environments
    # sharing one Upstash Redis instance (e.g. "production" and
    # "integration") from reading or writing each other's cached
    # ClinicalDecisions. Left unset by default so bootstrap.py can
    # derive it from AEGIS_PROFILE; set explicitly to override that
    # derivation (e.g. running two isolated integration suites against
    # the same Redis instance).
    REDIS_CACHE_NAMESPACE: str | None = Field(default=None)

    # Embedding <-> vector-index compatibility boundary. There is
    # intentionally no default in "production", "demo", or
    # "integration": an operator must state all three explicitly,
    # matching whatever actually populated the target Upstash Vector
    # index, rather than the application silently assuming a provider.
    # See EmbeddingConfiguration in api/bootstrap.py. "demo-local" has no
    # live external index to match against -- its compiled local index
    # is self-consistent by construction -- so these three default to
    # the same local model .env.example documents for every other
    # profile (SentenceTransformers, BAAI/bge-large-en-v1.5, 1024
    # dimensions) when left unset; see __init__ below.
    EMBEDDING_PROVIDER: str | None = Field(default=None)
    EMBEDDING_MODEL: str | None = Field(default=None)
    EMBEDDING_DIMENSIONS: int | None = Field(default=None, gt=0)
    # Only required when EMBEDDING_PROVIDER == "openai" -- checked below.
    OPENAI_API_KEY: SecretStr | None = Field(default=None)

    RETRIEVAL_TOP_K: int = Field(default=5, gt=0)
    RETRIEVAL_SIMILARITY_THRESHOLD: float | None = Field(default=None)

    # PHI/debug boundary for GET /api/v1/workflows/{workflow_id}: whether
    # that endpoint is even allowed to include raw RetrievalResult /
    # ReasoningContext / CodingRecommendation artifact payloads when a
    # caller additionally asks for them via ?include_artifacts=true (see
    # aegis.api.routers.workflow). Deliberately independent of
    # AEGIS_PROFILE, which selects runtime collaborators/infrastructure
    # wiring only and must not also become a data-visibility switch.
    # False in production; set true for demo/staging environments where
    # exposing internal AI execution traces is acceptable.
    EXPOSE_WORKFLOW_ARTIFACTS: bool = Field(default=False)

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

        # "demo-local" is the one profile with no live Upstash Vector
        # index to match, so its embedding configuration is safe to
        # default rather than require -- fill any unset value before the
        # missing-fields check below runs, so a fresh clone needs no
        # .env at all under this profile. Every other profile falls
        # through to the explicit-required checks unchanged.
        if self.AEGIS_PROFILE == "demo-local":
            if self.EMBEDDING_PROVIDER is None:
                self.EMBEDDING_PROVIDER = "sentence_transformers"
            if self.EMBEDDING_MODEL is None:
                self.EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
            if self.EMBEDDING_DIMENSIONS is None:
                self.EMBEDDING_DIMENSIONS = 1024

        missing_fields: list[str] = []

        if self.AEGIS_PROFILE in ("production", "integration"):
            if not self.GROQ_API_KEY or not self.GROQ_API_KEY.get_secret_value():
                missing_fields.append("GROQ_API_KEY")

            if not self.UPSTASH_REDIS_REST_URL:
                missing_fields.append("UPSTASH_REDIS_REST_URL")

            if (
                not self.UPSTASH_REDIS_REST_TOKEN
                or not self.UPSTASH_REDIS_REST_TOKEN.get_secret_value()
            ):
                missing_fields.append("UPSTASH_REDIS_REST_TOKEN")

        if self.AEGIS_PROFILE != "demo-local":
            if not self.UPSTASH_VECTOR_REST_URL:
                missing_fields.append("UPSTASH_VECTOR_REST_URL")

            if (
                not self.UPSTASH_VECTOR_REST_TOKEN
                or not self.UPSTASH_VECTOR_REST_TOKEN.get_secret_value()
            ):
                missing_fields.append("UPSTASH_VECTOR_REST_TOKEN")

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
