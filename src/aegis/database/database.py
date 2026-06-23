# src/aegis/database/database.py

import logging
import sqlite3
from pathlib import Path
from typing import Iterable

from aegis.database.connection import get_db_connection

logger = logging.getLogger("aegis.database")

# Resolve project-root-relative defaults so DB files live under the repository `data/` directory
ROOT_DIR = Path(__file__).resolve().parents[3]
MIGRATION_DIR = Path(__file__).parent / "migration"
DEFAULT_CLINICAL_DB_PATH = ROOT_DIR / "data" / "clinical_registry.db"
DEFAULT_GRAPH_DB_PATH = ROOT_DIR / "data" / "graph_state.db"

CLINICAL_MIGRATION_FILES = [
    "patient_identity_vault",
    "patient_case",
    "icd11_taxonomy_reference",
    "patient_extracted_code",
    "clinical_trial",
    "trial_target_code",
    "trial_match",
    "human_review_log",
]

GRAPH_MIGRATION_FILES = ["checkpoint_blob"]


def _execute_stepwise_scaffold(db_path: Path, migration_list: Iterable[str], force_drop: bool):
    """Discovers, reads, and executes external SQL migration assets.

    Uses `executescript` to allow multi-statement SQL files and relies on the
    connection context manager to commit/rollback atomically.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if force_drop and db_path.exists():
        logger.warning(f"⚠️ Destructive wipe requested. Evicting database at: {db_path}")
        db_path.unlink()

    # Use the centralized connection factory which sets PRAGMAs and handles commits
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        for schema_name in migration_list:
            try:
                logger.info(f"🔨 Compiling Table Component: {schema_name}...")
                ddl_script = load_schema(schema_name)

                # Execute multi-statement SQL safely
                cursor.executescript(ddl_script)
                logger.info(f"✅ Executed migration structural unit: [{schema_name}]")
            except FileNotFoundError:
                logger.error(f"❌ Migration asset missing from disk: {schema_name}")
                raise
            except sqlite3.Error as e:
                logger.error(f"❌ Compile error inside {schema_name}: {e}")
                raise


def init_all_databases(
    clinical_db: Path | None = None, graph_db: Path | None = None, force_drop: bool = False
):
    """Initialize both clinical and graph databases (paths default to project `data/`)."""
    clinical_db = Path(clinical_db) if clinical_db else DEFAULT_CLINICAL_DB_PATH
    graph_db = Path(graph_db) if graph_db else DEFAULT_GRAPH_DB_PATH

    init_clinical_database(clinical_db, force_drop=force_drop)
    init_graph_database(graph_db, force_drop=force_drop)


def init_clinical_database(db_path: Path | None = None, force_drop: bool = False):
    """Public execution hook to build the clinical schema suite from files."""
    target = Path(db_path) if db_path else DEFAULT_CLINICAL_DB_PATH
    _execute_stepwise_scaffold(target, CLINICAL_MIGRATION_FILES, force_drop)


def init_graph_database(db_path: Path | None = None, force_drop: bool = False):
    """Public execution hook to build the graph/state schema suite from files."""
    target = Path(db_path) if db_path else DEFAULT_GRAPH_DB_PATH
    _execute_stepwise_scaffold(target, GRAPH_MIGRATION_FILES, force_drop)


# Better Hygiene: Python only handles IO, not raw string accumulation
def load_schema(schema_name: str) -> str:
    """
    Safely retrieves raw DDL scripts from the local migration asset directory.
    Prevents raw string accumulation inside core Python execution modules.
    """
    # Enforce resolution relative to this specific module's directory tree
    schema_path = Path(__file__).parent / "migration" / f"{schema_name}.sql"

    if not schema_path.exists():
        error_msg = (
            f"❌ Critical Database Asset Missing: Expected SQL schema file at '{schema_path}'"
        )
        logger.critical(error_msg)
        raise FileNotFoundError(error_msg)

    try:
        return schema_path.read_text(encoding="utf-8")
    except OSError as e:
        logger.critical(f"❌ OS Context Read Failure on asset [{schema_name}]: {e}")
        raise
