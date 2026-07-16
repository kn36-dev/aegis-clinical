# Application bootstrap end to end: the FastAPI lifespan must open the
# clinical connection, assemble the AegisContainer, compile the graph,
# and store both on app.state -- exactly what routers retrieve via
# aegis.api.dependencies. Every collaborator that would otherwise need
# real SQLite migrations, Upstash, OpenAI, or Groq credentials is
# substituted with a fake/dependency override so this test never makes
# a network call.
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from langgraph.graph.state import CompiledStateGraph

from aegis.application.container import AegisContainer, build_container
from aegis.database.database import init_clinical_database
from tests.application.fakes import (
    FakeClinicalDecisionCacheRepository,
    FakeEmbeddingProvider,
    FakeICDCodeValidator,
    FakePHIAnonymizer,
    FakeReasoningProvider,
    FakeVectorQueryProvider,
)


class _FakeSettings:
    GRAPH_CHECKPOINT_DB_PATH: str
    RETRIEVAL_TOP_K = 3
    RETRIEVAL_SIMILARITY_THRESHOLD = None

    def __init__(self, graph_checkpoint_db_path: str) -> None:
        self.GRAPH_CHECKPOINT_DB_PATH = graph_checkpoint_db_path


@pytest.fixture
def bootstrapped_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[TestClient, AegisContainer]]:
    import aegis.api.main as main_module

    db_path = tmp_path / "clinical_registry.db"
    init_clinical_database(db_path)
    connection = sqlite3.connect(db_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON;")

    container = build_container(
        connection,
        cache_repository=FakeClinicalDecisionCacheRepository(),
        embedding_provider=FakeEmbeddingProvider(),
        vector_query_provider=FakeVectorQueryProvider(),
        reasoning_provider=FakeReasoningProvider(),
        reasoning_model_name="fake-model",
        icd_code_validator=FakeICDCodeValidator(),
        phi_anonymizer=FakePHIAnonymizer(),
    )
    settings = _FakeSettings(str(tmp_path / "graph_checkpoints.db"))

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "open_clinical_connection", lambda _settings: connection)
    monkeypatch.setattr(main_module, "build_infrastructure", lambda _settings, _conn: container)

    with TestClient(main_module.app) as client:
        yield client, container

    connection.close()


def test_lifespan_populates_app_state_container_and_graph(
    bootstrapped_client: tuple[TestClient, AegisContainer],
) -> None:
    import aegis.api.main as main_module

    _client, container = bootstrapped_client

    assert main_module.app.state.container is container
    assert isinstance(main_module.app.state.graph, CompiledStateGraph)


def test_health_endpoint_reports_booted_container_and_graph_ready(
    bootstrapped_client: tuple[TestClient, AegisContainer],
) -> None:
    client, _container = bootstrapped_client

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "booted": True,
        "container_ready": True,
        "graph_ready": True,
    }
