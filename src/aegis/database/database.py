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


def init_clinical_database(db_path: Path | None = None, force_drop: bool = False):
    """Public execution hook to build the clinical schema suite from files."""
    target = Path(db_path) if db_path else DEFAULT_CLINICAL_DB_PATH
    _execute_stepwise_scaffold(target, CLINICAL_MIGRATION_FILES, force_drop)


def init_graph_database(db_path: Path | None = None, force_drop: bool = False):
    """Public execution hook to build the graph/state schema suite from files."""
    target = Path(db_path) if db_path else DEFAULT_GRAPH_DB_PATH
    _execute_stepwise_scaffold(target, GRAPH_MIGRATION_FILES, force_drop)


def init_all_databases(clinical_db: Path | None = None, graph_db: Path | None = None, force_drop: bool = False):
    """Initialize both clinical and graph databases (paths default to project `data/`)."""
    clinical_db = Path(clinical_db) if clinical_db else DEFAULT_CLINICAL_DB_PATH
    graph_db = Path(graph_db) if graph_db else DEFAULT_GRAPH_DB_PATH

    init_clinical_database(clinical_db, force_drop=force_drop)
    init_graph_database(graph_db, force_drop=force_drop)

# ==========================================
# 🏢 DECOUPLED DDL REGISTER (1 Schema = 1 Entry)
# ==========================================

# CLINICAL_TABLE_SCHEMAS: Dict[str, str] = {
#     "Patient_identity_vault": """
#         CREATE TABLE IF NOT EXISTS Patient_identity_vault (
#             patient_id TEXT PRIMARY KEY,
#             medical_record_number TEXT UNIQUE NOT NULL,
#             first_name TEXT NOT NULL,
#             last_name TEXT NOT NULL,
#             date_of_birth DATE NOT NULL
#         );
#     """,
#     "Patient_cases": """
#         CREATE TABLE IF NOT EXISTS Patient_cases (
#             case_id TEXT PRIMARY KEY,
#             patient_id TEXT NOT NULL,
#             status TEXT NOT NULL CHECK (status IN ('pending_ai', 'pending_hitl', 'archived', 'failed')),
#             ingress_timestamp TEXT NOT NULL,
#             raw_clinical_note TEXT NOT NULL,
#             anonymized_clinical_note TEXT,
#             FOREIGN KEY (patient_id) REFERENCES Patient_identity_vault(patient_id)
#         );
#     """,
#     "ICD11_taxonomy_reference": """
#         CREATE TABLE IF NOT EXISTS ICD11_taxonomy_reference (
#             icd11_code TEXT PRIMARY KEY,
#             title TEXT NOT NULL,
#             hierarchical_path TEXT NOT NULL,
#             description TEXT
#         );
#     """,
#     "Patient_extracted_codes": """
#         CREATE TABLE IF NOT EXISTS Patient_extracted_codes (
#             case_id TEXT NOT NULL,
#             icd11_code TEXT NOT NULL,
#             confidence_score REAL NOT NULL CHECK (confidence_score BETWEEN 0.0 AND 1.0),
#             extraction_source TEXT NOT NULL,
#             PRIMARY KEY (case_id, icd11_code),
#             FOREIGN KEY (case_id) REFERENCES Patient_cases(case_id) ON DELETE CASCADE,
#             FOREIGN KEY (icd11_code) REFERENCES ICD11_taxonomy_reference(icd11_code)
#         );
#     """,
#     "Clinical_trial": """
#         CREATE TABLE IF NOT EXISTS Clinical_trial (
#             trial_id TEXT PRIMARY KEY,
#             title TEXT NOT NULL,
#             phase TEXT NOT NULL CHECK (phase IN ('Phase 1', 'Phase 2', 'Phase 3', 'Phase 4')),
#             sponsor TEXT NOT NULL,
#             status TEXT NOT NULL CHECK (status IN ('Recruiting', 'Completed', 'Suspended')),
#             raw_eligibility_criteria TEXT NOT NULL
#         );
#     """,
#     "Trial_Target_codes": """
#         CREATE TABLE IF NOT EXISTS Trial_Target_codes (
#             trial_id TEXT NOT NULL,
#             icd11_code TEXT NOT NULL,
#             criterion_type TEXT NOT NULL CHECK (criterion_type IN ('INCLUSION', 'EXCLUSION')),
#             PRIMARY KEY (trial_id, icd11_code),
#             FOREIGN KEY (trial_id) REFERENCES Clinical_trial(trial_id) ON DELETE CASCADE,
#             FOREIGN KEY (icd11_code) REFERENCES ICD11_taxonomy_reference(icd11_code)
#         );
#     """,
#     "Trial_Matches": """
#         CREATE TABLE IF NOT EXISTS Trial_Matches (
#             match_id TEXT PRIMARY KEY,
#             patient_id TEXT NOT NULL,
#             trigger_case_id TEXT NOT NULL,
#             trial_id TEXT NOT NULL,
#             structural_match_score REAL NOT NULL,
#             match_status TEXT NOT NULL CHECK (match_status IN ('PENDING_REVIEW', 'PHYSICIAN_APPROVED', 'PHYSICIAN_REJECTED')),
#             justification_summary TEXT NOT NULL,
#             created_at TEXT NOT NULL,
#             FOREIGN KEY (patient_id) REFERENCES Patient_identity_vault(patient_id),
#             FOREIGN KEY (trigger_case_id) REFERENCES Patient_cases(case_id) ON DELETE CASCADE,
#             FOREIGN KEY (trial_id) REFERENCES Clinical_trial(trial_id) ON DELETE CASCADE
#         );
#     """,
#     "Human_Review_Logs": """
#         CREATE TABLE IF NOT EXISTS Human_Review_Logs (
#             review_id TEXT PRIMARY KEY,
#             case_id TEXT NOT NULL,
#             reviewer_badge_id TEXT NOT NULL,
#             action_taken TEXT NOT NULL CHECK (action_taken IN ('APPROVED_ALL', 'OVERRIDDEN_AND_APPROVED', 'REJECTED_CASE')),
#             physician_notes TEXT,
#             cryptographic_signature TEXT NOT NULL,
#             timestamp TEXT NOT NULL,
#             FOREIGN KEY (case_id) REFERENCES Patient_cases(case_id)
#         );
#     """,
# }

# GRAPH_TABLE_SCHEMAS: Dict[str, str] = {
#     "checkpoint_blobs": """
#         CREATE TABLE IF NOT EXISTS checkpoint_blobs (
#             thread_id TEXT NOT NULL,
#             checkpoint_id TEXT NOT NULL,
#             parent_id TEXT,
#             checkpoint BLOB NOT NULL,
#             metadata BLOB NOT NULL,
#             PRIMARY KEY (thread_id, checkpoint_id)
#         );
#     """
# }

# ==========================================
# ⚙️ ORCHESTRATION ENGINE
# ==========================================


# def _execute_stepwise_scaffold(
#     db_path: Path, schema_registry: Dict[str, str], force_drop: bool, engine_desc: str
# ):
#     """Executes schema creation dynamically with atomic logging per individual table metadata."""
#     db_path.parent.mkdir(parents=True, exist_ok=True)

#     if force_drop and db_path.exists():
#         logger.warning(
#             f"⚠️ Destructive wipe requested for [{engine_desc}]. Evicting database at: {db_path}..."
#         )
#         try:
#             db_path.unlink()
#         except OSError as e:
#             logger.error(f"❌ Critical failure clearing database asset partition: {e}")
#             raise

#     logger.info(f"🚀 Initializing Orchestrated Run [{engine_desc}] at target location: {db_path}")
#     conn = sqlite3.connect(str(db_path))

#     try:
#         # Crucial for SQLite structural relational checking
#         conn.execute("PRAGMA foreign_keys = ON;")
#         cursor = conn.cursor()

#         # Stepwise construction loop for targeted individual-table trace visibility
#         for table_name, ddl_script in schema_registry.items():
#             logger.info(f"🔨 Compiling Table Component: {table_name}...")
#             cursor.execute(ddl_script)
#             logger.info(f"✅ Success -> Structural Component Built: [{table_name}]")

#         conn.commit()
#         logger.info(f"🎉 System Matrix [{engine_desc}] fully stabilized and compiled.\n")
#     except sqlite3.Error as e:
#         logger.error(
#             f"❌ Execution boundary fault during compilation runtime of [{engine_desc}]: {e}"
#         )
#         conn.rollback()
#         raise e
#     finally:
#         conn.close()


# def init_clinical_database(db_path: Path = DEFAULT_CLINICAL_DB_PATH, force_drop: bool = False):
#     """Orchestrates sequential relational building block operations for clinical tracking."""
#     _execute_stepwise_scaffold(
#         db_path, CLINICAL_TABLE_SCHEMAS, force_drop, "Clinical Core Relational Vault"
#     )


# def init_graph_database(db_path: Path = DEFAULT_GRAPH_DB_PATH, force_drop: bool = False):
#     """Orchestrates runtime state management persistence parameters for LangGraph."""
#     _execute_stepwise_scaffold(
#         db_path, GRAPH_TABLE_SCHEMAS, force_drop, "LangGraph Asynchronous Fabric"
#     )


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="Aegis-Clinical Multi-Paradigm Micro-Scaffolder")
#     parser.add_argument(
#         "--reset", action="store_true", help="Wipe and rebuild all schemas cleanly from scratch."
#     )
#     parser.add_argument("--clinical-path", type=str, default=str(DEFAULT_CLINICAL_DB_PATH))
#     parser.add_argument("--graph-path", type=str, default=str(DEFAULT_GRAPH_DB_PATH))

#     args = parser.parse_args()

#     init_clinical_database(db_path=Path(args.clinical_path), force_drop=args.reset)
#     init_graph_database(db_path=Path(args.graph_path), force_drop=args.reset)


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
