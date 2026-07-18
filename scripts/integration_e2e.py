#!/usr/bin/env python3
"""
Infrastructure-verification end-to-end run of the clinical pipeline
(submission -> AI reasoning -> human review -> decision -> cache
projection) through the real FastAPI app under ``AEGIS_PROFILE=integration``.

Runs the same workflow as ``make demo``, but selects the ``integration``
profile: real Redis-backed cache and real CrewAI/Groq reasoning replace
the deterministic in-memory adapters "demo" uses, so this verifies the
full set of external infrastructure credentials (Upstash Vector, Upstash
Redis, Groq) actually work, without changing any application logic.

This is a workflow-correctness script: it must always exercise the
full retrieval/reasoning/human-review/decision path, never take the
cache-hit shortcut. ``build_e2e_settings`` gives it a fresh
``integration-<uuid4()>`` Redis namespace every run (never deleting or
clearing Redis, never bypassing ``CacheService``) so that holds
structurally; ``main`` below also asserts it explicitly, so a
regression here fails loudly instead of silently skipping review. See
``scripts/integration_cache_e2e.py`` for the companion script that
deliberately exercises the cache-HIT path against a stable namespace.

The actual submission/review machinery lives in ``scripts/e2e_common.py``
-- this file only selects the integration profile and adds the
cache-MISS assertion. See that module's docstring for the prerequisite
ICD-11 taxonomy seeding step.

Usage:
    AEGIS_PROFILE=integration uv run python scripts/integration_e2e.py
"""

from __future__ import annotations

from e2e_common import (
    _require_seeded_taxonomy,
    build_e2e_settings,
    e2e_test_client,
    open_e2e_connection,
    submit_and_resolve,
)


def main() -> None:
    settings = build_e2e_settings()
    assert settings.AEGIS_PROFILE == "integration", (
        "integration_e2e.py must run under AEGIS_PROFILE=integration."
    )

    connection = open_e2e_connection(settings)
    _require_seeded_taxonomy(connection)

    with e2e_test_client(settings, connection) as (client, _container):
        result = submit_and_resolve(client, connection)
        assert not result.cache_hit, (
            "integration_e2e.py must always exercise a cache MISS, but got a "
            f"cache HIT under namespace {settings.REDIS_CACHE_NAMESPACE!r} -- the "
            "execution-scoped namespace was not applied."
        )
        print(f"case_id={result.case_id}")
        print(f"decision_id={result.decision_id}")

    connection.close()


if __name__ == "__main__":
    main()
