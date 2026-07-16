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

_KEY_PREFIX = "aegis:clinical-decision-cache:"
DEFAULT_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days


class UpstashClinicalDecisionCacheRepository:
    """
    ``ClinicalDecisionCacheRepository`` implementation backed by Upstash Redis.

    Structurally satisfies
    ``aegis.services.cache_service.ClinicalDecisionCacheRepository``
    (``get``, ``set``). Keys are namespaced under a fixed prefix so this
    repository can share a Redis instance with other future cache
    consumers without collision.
    """

    def __init__(self, url: str, token: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self._client = Redis(url=url, token=token)
        self._ttl_seconds = ttl_seconds

    def get(self, cache_key: str) -> ClinicalDecision | None:
        raw = self._client.get(_namespaced(cache_key))
        if raw is None:
            return None
        return ClinicalDecision.model_validate_json(raw)

    def set(self, cache_key: str, decision: ClinicalDecision) -> None:
        self._client.set(
            _namespaced(cache_key),
            decision.model_dump_json(),
            ex=self._ttl_seconds,
        )


def _namespaced(cache_key: str) -> str:
    return f"{_KEY_PREFIX}{cache_key}"
