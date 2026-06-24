from __future__ import annotations

from typing import Any


class UpstashRedisAdapter:
    """Thin adapter for Redis-style caching interactions."""

    def __init__(self, url: str | None = None, *, client: Any | None = None) -> None:
        self.url = url
        self._client = client

    def set(self, key: str, value: str) -> None:
        if self._client is None:
            raise RuntimeError("Redis client is not configured")
        self._client.set(key, value)

    def get(self, key: str) -> Any:
        if self._client is None:
            raise RuntimeError("Redis client is not configured")
        return self._client.get(key)


class UpstashVectorAdapter:
    """Thin adapter for vector database interactions."""

    def __init__(self, url: str | None = None, *, client: Any | None = None) -> None:
        self.url = url
        self._client = client

    def upsert(self, key: str, payload: dict[str, Any]) -> None:
        if self._client is None:
            raise RuntimeError("Vector client is not configured")
        self._client.upsert(key, payload)

    def query(self, text: str, *, top_k: int = 1) -> Any:
        if self._client is None:
            raise RuntimeError("Vector client is not configured")
        return self._client.query(text, top_k=top_k)
