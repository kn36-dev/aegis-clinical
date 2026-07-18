#!/usr/bin/env python3
"""
Redis cache-persistence verification run of the clinical pipeline
through the real FastAPI app under ``AEGIS_PROFILE=integration``.

Distinct from ``integration_e2e.py``, which verifies workflow
correctness and must always start from a cache MISS: this script's
entire purpose is to verify the opposite -- that a physician-approved
``ClinicalDecision`` really is durably cached in Redis and really is
served back on a second submission of the same logical observation,
short-circuiting the graph at ``cache_lookup`` (see
``aegis.graphs.workflow._route_after_cache_lookup``).

It therefore uses a stable Redis namespace (``CACHE_TEST_NAMESPACE``
below), not an execution-scoped random one -- the whole point is to
observe the SAME cache entry across two submissions. To keep repeated
runs of this script reliable (a stale entry from a previous run would
make "first submission -> cache MISS" flaky), it deletes exactly the
one deterministic key this run's own submission will use, before
submitting:

1. Compute that key the same way ``CacheService`` computes it --
   ``SHA256CacheKeyGenerator`` over the real, container-wired
   ``NormalizationService``'s output for the fixed sample note -- no
   independent reimplementation of canonicalization or hashing.
2. Delete only ``aegis:integration-cache-test:<that key>`` via the
   ``upstash_redis`` client directly. This never scans or clears the
   namespace, and it never adds a delete/invalidation method to
   ``CacheService`` or ``UpstashClinicalDecisionCacheRepository`` --
   both remain exactly as production uses them; only this script talks
   to Redis directly, and only for this one setup step.

Both submissions below go through ``CacheService`` normally via the
real HTTP boundary, exactly like ``integration_e2e.py``.

See ``scripts/e2e_common.py`` for the shared TestClient/submission
machinery this reuses.

Usage:
    AEGIS_PROFILE=integration uv run python scripts/integration_cache_e2e.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

# Mirrors e2e_common.py's own path setup -- required here too since
# this script, unlike demo_e2e.py/integration_e2e.py, imports ``aegis.*``
# directly rather than only importing from ``e2e_common``.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT))

from upstash_redis import Redis  # noqa: E402

from aegis.models.clinical_note import ClinicalNote  # noqa: E402
from aegis.services.cache_service import SHA256CacheKeyGenerator  # noqa: E402
from e2e_common import (  # noqa: E402
    _CONTENT_REFERENCE,
    _print_stage,
    _require_seeded_taxonomy,
    build_e2e_settings,
    e2e_test_client,
    open_e2e_connection,
    submit_and_resolve,
)

if TYPE_CHECKING:
    from aegis.application.container import AegisContainer
    from aegis.config import AppSettings

# Stable on purpose -- see module docstring. Not an execution-scoped
# uuid like integration_e2e.py's namespace, because this script needs
# the SAME namespace across both submissions below.
CACHE_TEST_NAMESPACE = "integration-cache-test"

# Mirrors UpstashClinicalDecisionCacheRepository's documented
# "aegis:<namespace>:<key>" key shape. Not imported from that adapter
# (it is a private module constant there) -- duplicated here only as a
# literal, since this script must not add any public surface to the
# adapter for test consumption.
_REDIS_KEY_PREFIX = "aegis"


def _compute_cache_key(container: AegisContainer, content_reference: str) -> str:
    """
    Compute the exact ``CacheService`` cache key for ``content_reference``.

    Builds a throwaway ``ClinicalNote`` -- only ``content_reference``
    matters here, since ``SHA256CacheKeyGenerator`` never reads
    ``case_id`` or ``patient_id`` -- and runs it through the real,
    container-wired ``NormalizationService``, so this reproduces
    exactly what ``cache_lookup``/``cache_store`` will compute during
    the actual submissions below.
    """
    dummy_note = ClinicalNote(
        case_id=uuid4(),
        patient_id=uuid4(),
        content_reference=content_reference,
        created_at=datetime.now(timezone.utc),
    )
    normalized_note = container.normalization_service.normalize(dummy_note)
    return SHA256CacheKeyGenerator().generate(normalized_note)


def _delete_stable_cache_entry(settings: AppSettings, cache_key: str) -> None:
    """
    Delete exactly the one deterministic Redis key this run will use.

    Talks to Upstash Redis directly -- not through ``CacheService`` or
    ``UpstashClinicalDecisionCacheRepository``, and adds no new method
    to either -- so a ``ClinicalDecision`` left over from a previous
    run of this same script cannot make "first submission -> cache
    MISS" flaky. Deletes only this single key; never scans or clears
    the namespace.
    """
    assert settings.UPSTASH_REDIS_REST_URL is not None
    assert settings.UPSTASH_REDIS_REST_TOKEN is not None
    redis_client = Redis(
        url=str(settings.UPSTASH_REDIS_REST_URL),
        token=settings.UPSTASH_REDIS_REST_TOKEN.get_secret_value(),
    )
    redis_key = f"{_REDIS_KEY_PREFIX}:{settings.REDIS_CACHE_NAMESPACE}:{cache_key}"
    redis_client.delete(redis_key)
    print(f"[CACHE TEST SETUP] deleted key={redis_key}")


def main() -> None:
    settings = build_e2e_settings(namespace=CACHE_TEST_NAMESPACE)
    assert settings.AEGIS_PROFILE == "integration", (
        "integration_cache_e2e.py must run under AEGIS_PROFILE=integration "
        "to exercise the real Redis-backed cache adapter."
    )

    connection = open_e2e_connection(settings)
    _require_seeded_taxonomy(connection)

    with e2e_test_client(settings, connection) as (client, container):
        cache_key = _compute_cache_key(container, _CONTENT_REFERENCE)
        _delete_stable_cache_entry(settings, cache_key)

        _print_stage("RUN 1 -- expect cache MISS (full workflow, human review)")
        first = submit_and_resolve(client, connection)
        assert not first.cache_hit, "expected RUN 1 to be a cache MISS"

        _print_stage("RUN 2 -- same namespace, same note -> expect cache HIT")
        second = submit_and_resolve(client, connection)
        assert second.cache_hit, "expected RUN 2 to be a cache HIT"
        assert second.decision_id == first.decision_id, (
            "cache HIT should serve back the exact ClinicalDecision RUN 1 persisted"
        )

    connection.close()
    print(
        "PASS: cache MISS on first submission, cache HIT on second submission "
        f"(namespace={CACHE_TEST_NAMESPACE!r})"
    )


if __name__ == "__main__":
    main()
