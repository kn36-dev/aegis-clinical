# src/aegis/api/main.py
"""
FastAPI application entry point.

Owns only wiring: FastAPI app construction, middleware, router
registration, and a lifespan that delegates all infrastructure
composition to ``aegis.api.bootstrap``. The lifespan's job is to run
once at startup -- open the clinical registry connection, build the
``AegisContainer``, compile the LangGraph workflow -- and store both on
``app.state`` as the application's single runtime instances. Routers
never construct services, repositories, or infrastructure themselves;
see ``aegis.api.dependencies``.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from aegis.api.bootstrap import build_infrastructure, open_clinical_connection
from aegis.api.routers import clinical, review
from aegis.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()

    connection = open_clinical_connection(settings)
    container = build_infrastructure(settings, connection)

    async with AsyncSqliteSaver.from_conn_string(settings.GRAPH_CHECKPOINT_DB_PATH) as saver:
        await saver.setup()

        app.state.container = container
        app.state.graph = container.build_graph(
            retrieval_top_k=settings.RETRIEVAL_TOP_K,
            retrieval_similarity_threshold=settings.RETRIEVAL_SIMILARITY_THRESHOLD,
            checkpointer=saver,
        )

        try:
            yield
        finally:
            connection.close()


app = FastAPI(title="Aegis Clinical Engine Core API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],  # Restrict access specifically to your React web client
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all systems endpoints under a single server execution context
app.include_router(clinical.router, prefix="/api/v1/clinical", tags=["Ingress"])
app.include_router(review.router, prefix="/api/v1/review", tags=["HITL Review"])


@app.get("/health")
def health_check() -> dict[str, bool]:
    """
    Lightweight readiness probe.

    Verifies only that the application booted, the container was
    assembled, and the graph compiled -- no SQLite, Redis, Upstash, or
    LLM connectivity checks. Those are exactly the checks
    ``EmbeddingCompatibilityError`` already enforces at startup, before
    the application ever begins accepting traffic.
    """
    return {
        "booted": True,
        "container_ready": hasattr(app.state, "container"),
        "graph_ready": hasattr(app.state, "graph"),
    }
