from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterator

import pytest

from aegis.database.database import init_clinical_database


@pytest.fixture
def clinical_db_connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """
    A fresh, fully-migrated clinical registry SQLite connection.

    Mirrors ``tests/infrastructure/sqlite/conftest.py``: each test gets
    its own on-disk database under pytest's per-test ``tmp_path``.
    """
    db_path = tmp_path / "clinical_registry.db"
    init_clinical_database(db_path, force_drop=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    yield conn
    conn.close()
