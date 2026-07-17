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

The actual workflow logic lives in ``scripts/e2e_common.py`` -- this file
only selects the integration profile by being the target the Makefile's
``integration`` recipe (``AEGIS_PROFILE=integration``) invokes. See that
module's docstring for the prerequisite ICD-11 taxonomy seeding step.

Usage:
    AEGIS_PROFILE=integration uv run python scripts/integration_e2e.py
"""

from __future__ import annotations

from e2e_common import main

if __name__ == "__main__":
    main()
