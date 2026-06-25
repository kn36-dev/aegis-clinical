from __future__ import annotations

import csv
import json
import logging
import re
from datetime import date
from pathlib import Path

from pydantic import BaseModel

from aegis.database.connection import get_db_connection
from aegis.database.database import init_clinical_database

logger = logging.getLogger("aegis.database.seeds")

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
    """Parse the WHO ICD-11 CSV export and upsert it into the taxonomy table."""
    db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
    csv_path = Path(csv_path) if csv_path else DEFAULT_CSV_PATH

    if not csv_path.exists():
        logger.warning("ICD-11 CSV source missing, skipping ICD seeding: %s", csv_path)
        return 0

    init_clinical_database(db_path=db_path, force_drop=False)

    records: list[tuple[str, str, str, str]] = []
    current_path_stack: list[str] = []

    with csv_path.open(mode="r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
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
                records.append((code, clean_title, class_kind, full_context_path))

    if not records:
        logger.info("No ICD-11 records parsed from %s", csv_path)
        return 0

    with get_db_connection(db_path) as conn:
        for code, title, class_kind, context_path in records:
            conn.execute(
                """
                INSERT INTO icd11_taxonomy_reference (code, title, class_kind, context_path)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    title = excluded.title,
                    class_kind = excluded.class_kind,
                    context_path = excluded.context_path;
                """,
                (code, title, class_kind, context_path),
            )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_icd11_code ON icd11_taxonomy_reference(code);")

    logger.info("Ingested %d ICD-11 records into %s", len(records), db_path)
    return len(records)


def seed_mock_cases(db_path: Path | str | None = None, json_path: Path | str | None = None) -> int:
    """Import mock clinical cases into the patient and case tables."""
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

    records = raw if isinstance(raw, list) else raw.get("cases", [])
    if not records:
        logger.info("No mock cases found in %s", json_path)
        return 0

    init_clinical_database(db_path=db_path, force_drop=False)

    inserted = 0
    with get_db_connection(db_path) as conn:
        for case in records:
            patient_id = case.get("patient_id")
            if not patient_id:
                continue
            case_id = case.get("case_id") or patient_id
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO patient_identity_vault (
                        patient_id,
                        medical_record_number,
                        first_name,
                        last_name,
                        date_of_birth
                    ) VALUES (?, ?, ?, ?, ?);
                    """,
                    (
                        patient_id,
                        case.get("medical_record_number"),
                        case.get("first_name"),
                        case.get("last_name"),
                        case.get("date_of_birth"),
                    ),
                )
                conn.execute(
                    """
                    INSERT OR IGNORE INTO patient_case (
                        patient_id,
                        case_id,
                        status,
                        ingress_timestamp,
                        raw_clinical_note,
                        anonymized_clinical_note
                    ) VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (
                        patient_id,
                        case_id,
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


def seed_all(db_path: Path | str | None = None) -> dict[str, int]:
    db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
    icd_count = seed_icd11(db_path=db_path)
    cases_count = seed_mock_cases(db_path=db_path)
    return {"icd": icd_count, "cases": cases_count}


class MockPatientCaseSchema(BaseModel):
    """Declarative validation boundary for incoming AI/Mock JSON payloads."""

    patient_id: str
    medical_record_number: str
    first_name: str
    last_name: str
    date_of_birth: date
    case_id: str
    status: str = "pending_ai"
    ingress_timestamp: str
    raw_clinical_note: str
    anonymized_clinical_note: str | None = None
