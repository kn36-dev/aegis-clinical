from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Iterator

import pytest

from aegis.database.database import init_clinical_database

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def clinical_db_connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """
    A fresh, fully-migrated clinical registry SQLite connection.

    Each test gets its own on-disk database under pytest's per-test
    ``tmp_path``, giving genuine test isolation without relying on shared
    or in-memory global state.
    """
    db_path = tmp_path / "clinical_registry.db"
    init_clinical_database(db_path, force_drop=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    yield conn
    conn.close()
