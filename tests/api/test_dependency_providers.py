# Tests the FastAPI dependency providers routers use to retrieve the
# application-wide container/graph from app.state, instead of
# constructing services, repositories, or infrastructure themselves.
from types import SimpleNamespace

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from aegis.api.dependencies import get_container, get_graph


def test_get_container_returns_request_app_state_container() -> None:
    expected_container = object()
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(container=expected_container))
    )

    assert get_container(request) is expected_container  # type: ignore[arg-type]


def test_get_graph_returns_request_app_state_graph() -> None:
    expected_graph = object()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(graph=expected_graph)))

    assert get_graph(request) is expected_graph  # type: ignore[arg-type]


def test_get_container_resolves_through_fastapi_dependency_injection() -> None:
    """
    Proves the wiring end to end through FastAPI's own DI machinery,
    not just direct python attribute access: a route depending on
    ``get_container``/``get_graph`` must receive exactly what startup
    stored on ``app.state``, without instantiating anything itself.
    """
    expected_container = object()
    expected_graph = object()
    test_app = FastAPI()
    test_app.state.container = expected_container
    test_app.state.graph = expected_graph

    @test_app.get("/probe")
    def probe(
        container: object = Depends(get_container),
        graph: object = Depends(get_graph),
    ) -> dict[str, bool]:
        return {
            "container_is_expected": container is expected_container,
            "graph_is_expected": graph is expected_graph,
        }

    with TestClient(test_app) as client:
        response = client.get("/probe")

    assert response.status_code == 200
    assert response.json() == {"container_is_expected": True, "graph_is_expected": True}
