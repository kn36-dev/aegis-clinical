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

import aiosqlite
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from aegis.api.bootstrap import build_infrastructure, open_clinical_connection
from aegis.api.routers import clinical, demo, review
from aegis.common.logging import get_logger
from aegis.config import get_settings
from aegis.graphs.checkpoint_serde import build_checkpoint_serializer

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()

    connection = open_clinical_connection(settings)
    container = build_infrastructure(settings, connection)

    async with aiosqlite.connect(settings.GRAPH_CHECKPOINT_DB_PATH) as conn:
        saver = AsyncSqliteSaver(conn, serde=build_checkpoint_serializer())
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
app.include_router(clinical.router, prefix="/api/v1", tags=["Ingress"])
app.include_router(review.router, prefix="/api/v1/reviews", tags=["HITL Review"])
app.include_router(demo.router, prefix="/api/v1/demo", tags=["Demo"])


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Last-resort error boundary.

    Routers already translate every known failure point (graph
    invocation, state retrieval/resume) into a specific ``HTTPException``
    via their own try/except blocks -- this handler only catches what
    those don't: bugs and unanticipated/malformed workflow state that
    would otherwise propagate as a raw traceback. It guarantees every
    response leaving the API, not just the ones routers anticipated,
    stays inside the same ``{"detail": ...}`` contract and never leaks
    stack traces, SQL/Redis error text, or other internals.
    """
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})


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
