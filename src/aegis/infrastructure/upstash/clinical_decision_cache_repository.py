"""
UpstashClinicalDecisionCacheRepository

Concrete ``ClinicalDecisionCacheRepository`` adapter
(``aegis.services.cache_service``) backed by Upstash Redis.

Owned exclusively by ``CacheService`` -- ``PersistenceService`` and
every other application service remain unaware that Redis exists (see
CLAUDE.md's defining principle and
application_service_contracts/cache_service.md's Persistence
Boundary). This adapter owns JSON serialization, key namespacing, and
TTL application only -- no cache-key generation
(``CacheService``/``SHA256CacheKeyGenerator`` owns that) and no
business logic about what belongs in the cache.
"""

from __future__ import annotations

from upstash_redis import Redis

from aegis.models.clinical_decision import ClinicalDecision

_KEY_PREFIX = "aegis"
DEFAULT_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days
DEFAULT_NAMESPACE = "clinical-decision-cache"


class UpstashClinicalDecisionCacheRepository:
    """
    ``ClinicalDecisionCacheRepository`` implementation backed by Upstash Redis.

    Structurally satisfies
    ``aegis.services.cache_service.ClinicalDecisionCacheRepository``
    (``get``, ``set``). Keys are namespaced under ``aegis:<namespace>:``
    so this repository can share a single Redis instance across runtime
    environments (e.g. "production" and "integration") -- or with other
    future cache consumers -- without collision. ``namespace`` is
    supplied by the caller (``api/bootstrap.py``, from configuration);
    this class only applies it, it never decides what the namespace
    should be.
    """

    def __init__(
        self,
        url: str,
        token: str,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        namespace: str = DEFAULT_NAMESPACE,
    ) -> None:
        self._client = Redis(url=url, token=token)
        self._ttl_seconds = ttl_seconds
        self._namespace = namespace

    def get(self, cache_key: str) -> ClinicalDecision | None:
        raw = self._client.get(self._namespaced(cache_key))

        if raw is None:
            return None
        return ClinicalDecision.model_validate_json(raw)

    def set(self, cache_key: str, decision: ClinicalDecision) -> None:
        self._client.set(
            self._namespaced(cache_key),
            decision.model_dump_json(),
            ex=self._ttl_seconds,
        )

    def _namespaced(self, cache_key: str) -> str:
        return f"{_KEY_PREFIX}:{self._namespace}:{cache_key}"
