# Tests the dependency provider functions that FastAPI injects into routes
# 1. `get_chat_model()` returns a configured model
# 2. `get_vector_client()` is cached (`lru_cache`)
# 3. `get_redis_client()` is cached
# 4. Graph checkpointer dependency retrievs the lifespan object correctly
# 5. `get_chat_model()` should also be cached
# Slight example: assert get_chat_model() is get_chat_model() and for vector and redis, this proves
# that the dependency provider behave as singletons throughout the application's lifetime

import importlib
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest


@pytest.fixture
def deps_module(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("UPSTASH_VECTOR_REST_URL", "https://vector.example.com")
    monkeypatch.setenv("UPSTASH_VECTOR_REST_TOKEN", "vector-token")
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "https://redis.example.com")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "redis-token")
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("LLM_MODEL", "test-model")

    sys.modules.pop("aegis.api.dependencies", None)
    sys.modules.pop("aegis.config", None)

    module = importlib.import_module("aegis.api.dependencies")
    module.get_chat_model.cache_clear()
    module.get_vector_client.cache_clear()
    module.get_redis_client.cache_clear()
    return module


def test_get_chat_model_returns_configured_model(deps_module):
    dummy_model = object()

    with patch.object(deps_module, "init_chat_model", return_value=dummy_model) as init_chat_model:
        model = deps_module.get_chat_model()

    assert model is dummy_model
    init_chat_model.assert_called_once_with(
        model="test-model",
        model_provider="groq",
        api_key="test-groq-key",
        temperature=0.0,
    )


def test_get_vector_client_is_cached(deps_module):
    with patch.object(deps_module, "Index", side_effect=lambda **kwargs: object()) as index_cls:
        first = deps_module.get_vector_client()
        second = deps_module.get_vector_client()

    assert first is second
    assert index_cls.call_count == 1


def test_get_redis_client_is_cached(deps_module):
    with patch.object(deps_module, "Redis", side_effect=lambda **kwargs: object()) as redis_cls:
        first = deps_module.get_redis_client()
        second = deps_module.get_redis_client()

    assert first is second
    assert redis_cls.call_count == 1


def test_get_graph_checkpointer_returns_request_state(deps_module):
    expected_checkpointer = object()
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(graph_checkpointer=expected_checkpointer))
    )

    assert deps_module.get_graph_checkpointer(request) is expected_checkpointer


def test_get_chat_model_is_cached(deps_module):
    with patch.object(
        deps_module, "init_chat_model", side_effect=[object(), object()]
    ) as init_chat_model:
        first = deps_module.get_chat_model()
        second = deps_module.get_chat_model()

    assert first is second
    assert init_chat_model.call_count == 1
