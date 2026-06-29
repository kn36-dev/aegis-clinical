# src/aegis/api/dependencies.py
import os
from functools import lru_cache

from fastapi import Request
from langchain.chat_models import init_chat_model
from upstash_redis import Redis
from upstash_vector import Index

from aegis.config import settings


@lru_cache
def get_chat_model():
    """
    Returns the application's default chat model.

    The concrete provider (Groq, OpenAI, Gemini, etc.)
    is selected entirely through configuration.
    """

    return init_chat_model(
        model=settings.LLM_MODEL,
        model_provider=settings.LLM_PROVIDER,
        api_key=settings.GROQ_API_KEY.get_secret_value(),
        temperature=0.0,
    )


@lru_cache
def get_vector_client() -> Index:
    """
    Returns a singleton Upstash Vector client.
    """

    return Index(
        url=str(settings.UPSTASH_VECTOR_REST_URL),
        token=settings.UPSTASH_VECTOR_REST_TOKEN.get_secret_value(),
    )


@lru_cache
def get_redis_client() -> Redis:
    """
    Returns a singleton Upstash Redis client.
    """

    return Redis(
        url=str(settings.UPSTASH_REDIS_REST_URL),
        token=settings.UPSTASH_REDIS_REST_TOKEN.get_secret_value(),
    )


def get_llm_client():
    # Enforces strict configuration tracking across system updates
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("CRITICAL: Missing system LLM_API_KEY environment variable.")

    return init_chat_model(
        model="qwen/qwen3-32b",
        model_provider="groq",
        temperature=0.0,  # Zero temperature ensures structural determinism
        api_key=settings.GROQ_API_KEY.get_secret_value(),
    )


def get_graph_checkpointer(request: Request):
    """
    Retrieves the shared LangGraph checkpoint manager
    attached during FastAPI startup.
    """

    return request.app.state.graph_checkpointer
