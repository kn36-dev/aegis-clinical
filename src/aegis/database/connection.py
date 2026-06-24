from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

logger = logging.getLogger("aegis.database")


@contextmanager
def get_db_connection(db_path: Path | str) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection and enforce the required PRAGMA settings."""
    target_path = Path(db_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    logger.debug("Opening SQLite connection to %s", target_path)

    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        yield conn
        conn.commit()
    except sqlite3.Error as exc:
        logger.error("Database transaction fault: %s", exc)
        conn.rollback()
        raise
    finally:
        conn.close()
