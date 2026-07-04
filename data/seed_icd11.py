# data/seed_icd11.py

import csv
import os
import re
import sqlite3
from typing import List

from aegis.database.repositories.icd_repository import ICDRepository
from aegis.database.repositories.models import ICDTaxonomyRecord

CSV_FILE_PATH = "data/icd11_mms_simplified.csv"
DB_FILE_PATH = "data/clinical_registry.db"


def calculate_depth_and_clean_title(raw_title: str) -> tuple[int, str]:
    match = re.match(r"^[\s-]*", raw_title)
    dashes_string = match.group(0) if match else ""
    depth = dashes_string.count("-")

    clean_title = raw_title.lstrip("- ").strip().strip('"')
    return depth, clean_title


def seed_icd11_taxonomy():
    print("🛡️ Starting ICD-11 ingestion (repository-driven)...")

    if not os.path.exists(CSV_FILE_PATH):
        raise FileNotFoundError(f"Missing: {CSV_FILE_PATH}")

    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()

    # Keep schema creation here (still acceptable at seed boundary)
    cursor.execute("DROP TABLE IF EXISTS icd11_taxonomy;")

    cursor.execute("""
        CREATE TABLE icd11_taxonomy (
            code TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            class_kind TEXT NOT NULL,
            context_path TEXT,
            block_id TEXT,
            chapter_no TEXT,
            is_leaf INTEGER,
            is_residual INTEGER,
            grouping_1 TEXT,
            grouping_2 TEXT,
            grouping_3 TEXT,
            grouping_4 TEXT,
            grouping_5 TEXT,
            foundation_uri TEXT,
            linearization_uri TEXT
        );
    """)

    repo = ICDRepository(conn)

    current_path_stack: List[str] = []
    records: List[ICDTaxonomyRecord] = []

    with open(CSV_FILE_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            raw_title = row.get("Title", "")
            code = (row.get("Code") or "").strip()
            class_kind = (row.get("ClassKind") or "").strip()

            if not raw_title:
                continue

            depth, clean_title = calculate_depth_and_clean_title(raw_title)

            if depth < len(current_path_stack):
                current_path_stack = current_path_stack[:depth]
            elif depth == len(current_path_stack):
                if current_path_stack:
                    current_path_stack.pop()

            current_path_stack.append(clean_title)

            context_path = " > ".join(current_path_stack)

            if code and code != "_NOCODEASSIGNED":
                records.append(
                    ICDTaxonomyRecord(
                        code=code,
                        title=clean_title,
                        class_kind=class_kind,
                        context_path=context_path,
                    )
                )

    repo.bulk_insert(records)

    conn.commit()
    conn.close()

    print(f"✅ Seed complete: {len(records)} ICD records inserted.")


if __name__ == "__main__":
    seed_icd11_taxonomy()
