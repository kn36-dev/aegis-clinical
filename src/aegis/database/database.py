from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Iterable

from aegis.database.connection import get_db_connection

logger = logging.getLogger("aegis.database")

ROOT_DIR = Path(__file__).resolve().parents[3]
MIGRATION_DIR = Path(__file__).parent / "migration"
DEFAULT_CLINICAL_DB_PATH = ROOT_DIR / "data" / "clinical_registry.db"
DEFAULT_GRAPH_DB_PATH = ROOT_DIR / "data" / "graph_state.db"

CLINICAL_MIGRATION_FILES = [
    "0001_init_patient_identity_vault",
    "0002_init_patient_case",
    "0003_init_icd11_taxonomy_reference",
    "0004_init_patient_extracted_code",
    "0005_init_clinical_trial",
    "0006_init_trial_target_code",
    "0007_init_trial_match",
    "0008_init_human_review_log",
]

GRAPH_MIGRATION_FILES = ["0001_init_checkpoint_blob"]


def _execute_stepwise_scaffold(
    db_path: Path | str, migration_list: Iterable[str | Path], force_drop: bool
) -> None:
    """Execute ordered SQL migrations against the provided SQLite database."""
    target_path = Path(db_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if force_drop and target_path.exists():
        logger.warning("Destructive wipe requested for %s", target_path)
        target_path.unlink()

    with get_db_connection(target_path) as conn:
        for schema_name in migration_list:
            logger.info("Applying migration %s", schema_name)
            ddl_script = load_schema(schema_name)
            conn.executescript(ddl_script)


def init_all_databases(
    clinical_db: Path | str | None = None,
    graph_db: Path | str | None = None,
    force_drop: bool = False,
) -> None:
    """Initialize clinical and graph databases using the ordered migration suite."""
    clinical_target = Path(clinical_db) if clinical_db else DEFAULT_CLINICAL_DB_PATH
    graph_target = Path(graph_db) if graph_db else DEFAULT_GRAPH_DB_PATH
    init_clinical_database(clinical_target, force_drop=force_drop)
    init_graph_database(graph_target, force_drop=force_drop)


def init_clinical_database(db_path: Path | str | None = None, force_drop: bool = False) -> None:
    """Public hook to build the clinical schema suite from migration files."""
    target = Path(db_path) if db_path else DEFAULT_CLINICAL_DB_PATH
    _execute_stepwise_scaffold(target, CLINICAL_MIGRATION_FILES, force_drop)


def init_graph_database(db_path: Path | str | None = None, force_drop: bool = False) -> None:
    """Public hook to build the graph/state schema suite from migration files."""
    target = Path(db_path) if db_path else DEFAULT_GRAPH_DB_PATH
    _execute_stepwise_scaffold(target, GRAPH_MIGRATION_FILES, force_drop)


def load_schema(schema_name: str | Path) -> str:
    """Read a migration file from the local migration directory."""
    candidate = Path(schema_name)
    if not candidate.suffix:
        candidate = candidate.with_suffix(".sql")

    schema_path = candidate if candidate.is_absolute() else MIGRATION_DIR / candidate.name
    if not schema_path.exists():
        error_msg = f"Missing migration asset: {schema_path}"
        logger.critical(error_msg)
        raise FileNotFoundError(error_msg)

    return schema_path.read_text(encoding="utf-8")


def get_database_status(
    clinical_db: Path | str | None = None, graph_db: Path | str | None = None
) -> dict[str, object]:
    """Return file existence and table inventory for the database files."""
    clinical_target = Path(clinical_db) if clinical_db else DEFAULT_CLINICAL_DB_PATH
    graph_target = Path(graph_db) if graph_db else DEFAULT_GRAPH_DB_PATH

    def _tables_for(path: Path) -> list[str]:
        if not path.exists():
            return []
        with sqlite3.connect(path) as conn:
            rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return [row[0] for row in rows]

    return {
        "clinical_exists": clinical_target.exists(),
        "graph_exists": graph_target.exists(),
        "clinical_tables": _tables_for(clinical_target),
        "graph_tables": _tables_for(graph_target),
    }
