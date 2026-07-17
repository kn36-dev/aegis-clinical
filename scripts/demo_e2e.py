#!/usr/bin/env python3
"""
Credential-light, real-retrieval end-to-end run of the clinical pipeline
(submission -> AI reasoning -> human review -> decision -> cache
projection) through the real FastAPI app under ``AEGIS_PROFILE=demo``.

The actual workflow logic lives in ``scripts/e2e_common.py`` -- this file
only selects the demo profile by being the target the Makefile's ``demo``
recipe (``AEGIS_PROFILE=demo``) invokes. See that module's docstring for
what "demo" does and does not fake, and for the prerequisite ICD-11
taxonomy seeding step.

Usage:
    AEGIS_PROFILE=demo uv run python scripts/demo_e2e.py
"""

from __future__ import annotations

from e2e_common import main

if __name__ == "__main__":
    main()
