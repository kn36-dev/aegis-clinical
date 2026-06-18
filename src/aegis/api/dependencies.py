# src/aegis/api/dependencies.py
import os

from fastapi import Request
from langchain.chat_models import init_chat_model

from aegis.config import settings


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
    return request.app.state.graph_checkpointer


def get_vector_client():
    """
    Example of how you extract your new Upstash variables anywhere in your app.
    """
    # Converting the HttpUrl object back to a clean string for an external SDK client
    url_string = str(settings.UPSTASH_VECTOR_REST_URL)
    token_string = settings.UPSTASH_VECTOR_REST_TOKEN.get_secret_value()

    return f"Connected to vector engine at {url_string} safely 🚀"
