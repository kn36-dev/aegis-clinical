# src/aegis/database/connection.py or database.py
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger("aegis.database")


@contextmanager
def get_db_connection(db_path: Path):
    """
    Centralized Database Connection Factory.
    Enforces production WAL performance thresholds and handles automatic cleanup.
    """
    db_path_str = str(db_path)
    logger.debug(f"🔌 Opening optimization pipeline to SQLite instance: {db_path_str}")

    conn = sqlite3.connect(db_path_str)
    try:
        # Enforce performance guardrails across all connection users
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")

        # Yield execution back to the caller block (e.g., a cursor operation)
        yield conn

        # Automatically commit transactions if no exceptions occurred
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"❌ Database boundary transaction fault encountered: {e}")
        conn.rollback()
        raise
    finally:
        # Guarantee closure of the file handle under all lifecycle conditions
        conn.close()
        logger.debug("🔌 Connection recycled safely to connection pool context.")
