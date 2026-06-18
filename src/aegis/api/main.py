# src/aegis/api/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from aegis.api.routers import clinical, review


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Consolidated Lifespan Management
    checkpoint_db_path = "data/graph_checkpoints.db"
    async with AsyncSqliteSaver.from_conn_string(checkpoint_db_path) as saver:
        await saver.setup()
        app.state.graph_checkpointer = saver
        print("🔒 Durable LangGraph AsyncSqliteSaver fully initialized.")
        yield


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


@app.get("/api/v1/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy", "engine": "LangGraph Active", "security": "HIPAA Guarded"}
