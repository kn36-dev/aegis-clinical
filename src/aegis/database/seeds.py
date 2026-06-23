import csv
import json
import logging
import re
from pathlib import Path
from typing import List

# From Pydantic, use this to validate better
# from pydantic import BaseModel, Field
from aegis.database.connection import get_db_connection

logger = logging.getLogger("aegis.database.seeds")

# Defaults relative to repository root
ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_CSV_PATH = ROOT_DIR / "data" / "icd11_mms_simplified.csv"
DEFAULT_JSON_PATH = ROOT_DIR / "data" / "mock_clinical_cases.json"
DEFAULT_DB_PATH = ROOT_DIR / "data" / "clinical_registry.db"


def _calculate_depth_and_clean_title(raw_title: str) -> tuple[int, str]:
    match = re.match(r"^[\s-]*", raw_title)
    dashes_string = match.group(0) if match else ""
    depth = dashes_string.count("-")
    clean_title = raw_title.lstrip("- ").strip().strip('"')
    return depth, clean_title


def seed_icd11(db_path: Path | str | None = None, csv_path: Path | str | None = None) -> int:
    """Parse the WHO ICD-11 CSV export and bulk-insert into the
    `ICD11_taxonomy_reference` table. Returns number of records inserted.
    """
    db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
    csv_path = Path(csv_path) if csv_path else DEFAULT_CSV_PATH

    if not csv_path.exists():
        logger.warning("ICD-11 CSV source missing, skipping ICD seeding: %s", csv_path)
        return 0

    records: List[tuple[str, str, str, str]] = []
    current_path_stack: List[str] = []

    with csv_path.open(mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_title = row.get("Title", "")
            code = (row.get("Code") or "").strip()
            class_kind = (row.get("ClassKind") or "").strip()

            if not raw_title:
                continue

            depth, clean_title = _calculate_depth_and_clean_title(raw_title)

            if depth < len(current_path_stack):
                current_path_stack = current_path_stack[:depth]
            elif depth == len(current_path_stack):
                if current_path_stack:
                    current_path_stack.pop()

            current_path_stack.append(clean_title)
            full_context_path = " > ".join(current_path_stack)

            if code and code != "_NOCODEASSIGNED":
                records.append((code, clean_title, full_context_path, class_kind))

    if not records:
        logger.info("No ICD-11 records parsed from %s", csv_path)
        return 0

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT OR REPLACE INTO ICD11_taxonomy_reference
                (icd11_code, title, hierarchical_path, description)
            VALUES (?, ?, ?, ?);
            """,
            records,
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_icd11_code ON ICD11_taxonomy_reference(icd11_code);"
        )

    logger.info("🎉 Ingested %d ICD-11 records into %s", len(records), db_path)
    return len(records)


def seed_mock_cases(db_path: Path | str | None = None, json_path: Path | str | None = None) -> int:
    """Minimal stub to import mock clinical cases from JSON into the
    `Patient_identity_vault` and `Patient_cases` tables.
    Returns number of cases inserted.
    """
    db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
    json_path = Path(json_path) if json_path else DEFAULT_JSON_PATH

    if not json_path.exists():
        logger.info("Mock cases JSON missing, skipping: %s", json_path)
        return 0

    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Mock cases JSON invalid or empty: %s", json_path)
        return 0

    # Accept either a top-level list or a dict with 'cases' key
    records = raw if isinstance(raw, list) else raw.get("cases", [])
    if not records:
        logger.info("No mock cases found in %s", json_path)
        return 0

    inserted = 0
    with get_db_connection(db_path) as conn:
        cur = conn.cursor()
        for case in records:
            # Expect minimal keys: patient_id, medical_record_number, first_name, last_name, date_of_birth
            pid = case.get("patient_id")
            if not pid:
                continue

            try:
                # We can validate the raw JSON structure instantly
                # Case = MockPatientCaseSchema(**raw_case)

                cur.execute(
                    "INSERT OR IGNORE INTO Patient_identity_vault (patient_id, medical_record_number, first_name, last_name, date_of_birth) VALUES (?, ?, ?, ?, ?);",
                    (
                        pid,
                        case.get("medical_record_number"),
                        case.get("first_name"),
                        case.get("last_name"),
                        case.get("date_of_birth"),
                    ),
                )

                cur.execute(
                    "INSERT OR IGNORE INTO Patient_cases (case_id, patient_id, status, ingress_timestamp, raw_clinical_note, anonymized_clinical_note) VALUES (?, ?, ?, ?, ?, ?);",
                    (
                        case.get("case_id"),
                        pid,
                        case.get("status", "pending_ai"),
                        case.get("ingress_timestamp"),
                        case.get("raw_clinical_note"),
                        case.get("anonymized_clinical_note"),
                    ),
                )

                inserted += 1
            except Exception:
                logger.exception("Failed inserting mock case: %s", case)

    logger.info("Inserted %d mock cases into %s", inserted, db_path)
    return inserted


# Main entry
def seed_all(db_path: Path | str | None = None) -> dict:
    db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
    icd_count = seed_icd11(db_path=db_path)
    cases_count = seed_mock_cases(db_path=db_path)
    return {"icd": icd_count, "cases": cases_count}


from datetime import date

from pydantic import BaseModel


class MockPatientCaseSchema(BaseModel):
    """Declarative validation boundary for incoming AI/Mock JSON payloads."""

    patient_id: str
    medical_record_number: str
    first_name: str
    last_name: str
    date_of_birth: (
        date  # Pydantic will auto-parse strings like "1990-01-01" into actual date objects
    )
    case_id: str
    status: str = "pending_ai"
    ingress_timestamp: str
    raw_clinical_note: str
    anonymized_clinical_note: str | None = None
