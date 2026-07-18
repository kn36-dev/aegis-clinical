#!/usr/bin/env python3
"""
One-time diagnostic: print the ``StructuredProseRepresentation`` text a
given ICD-11 code currently produces from the live SQLite taxonomy
state, alongside the raw ``context_path`` it was built from.

Purely local -- no embedding provider, no Upstash. Useful for
inspecting representation-building output directly (e.g. confirming
the ">"/"→" separator fix in
``aegis.indexing.representations.structured_prose``) without needing
network credentials. For comparing this output against what is
actually stored in the vector index, see
``scripts/verify_vector_consistency.py``.

Usage:
    uv run python scripts/verify_representation_consistency.py [CODE]

    CODE defaults to "1A08".
"""

from __future__ import annotations

import sqlite3
import sys

from aegis.config import get_settings
from aegis.database.repositories.icd_repository import ICDRepository
from aegis.indexing.builders import RepresentationBuilder
from aegis.indexing.representations.structured_prose import StructuredProseRepresentation

DEFAULT_CODE = "1A08"
BANNER = "=" * 32


def main() -> None:
    code = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CODE

    settings = get_settings()
    connection = sqlite3.connect(settings.CLINICAL_DB_PATH)
    try:
        record = ICDRepository(connection=connection).get_by_code(code)
        if record is None:
            print(
                f"\n[FAILED] ICD code {code!r} was not found in "
                f"{settings.CLINICAL_DB_PATH} (table icd11_taxonomy).\n"
            )
            sys.exit(1)
            return

        representation = RepresentationBuilder(strategy=StructuredProseRepresentation()).build(
            record
        )

        print(BANNER)
        print("AEGIS Representation Consistency Check")
        print(BANNER)
        print(f"\nCode:\n{code}")
        print(f"\nSQLite context_path:\n{record.context_path}")
        print(f"\nGenerated representation text:\n{representation.text}")
        print(BANNER)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
