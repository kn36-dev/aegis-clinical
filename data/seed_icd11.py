# data/seed_icd11.py

import csv
import os
import re
import sqlite3
from typing import List

# Configuration paths mapped to project template
CSV_FILE_PATH = "data/icd11_mms_simplified.csv"
DB_FILE_PATH = "data/clinical_registry.db"


def calculate_depth_and_clean_title(raw_title: str) -> tuple[int, str]:
    """
    Calculates tree depth by tracking the count of visual structural dashes
    and returns a clean string stripped of formatting elements.
    """

    # Count the leading dashes representing hierarchy depth
    match = re.match(re.compile(r"^[\s-]*"), raw_title)
    dashes_string = match.group(0) if match else ""
    depth = dashes_string.count("-")

    # Strip away formatting dashes, whitespace, and wrapping quotes
    clean_title = raw_title.lstrip("- ").strip().strip('"')
    return depth, clean_title


def seed_icd11_taxonomy():
    print("🛡️ Starting ICD-11 Reference Table ingestion...")

    if not os.path.exists(CSV_FILE_PATH):
        raise FileNotFoundError(
            f"Missing source file at: {CSV_FILE_PATH}. Place the WHO export here."
        )

    # Establish connection with the application SQLite database file
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()

    # Drop existing table to ensure state idempotency during pipeline re-runs
    cursor.execute("DROP TABLE IF EXISTS icd11_taxonomy;")
    cursor.execute("""
        CREATE TABLE icd11_taxonomy (
            code TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            class_kind TEXT NOT NULL,
            context_path TEXT NOT NULL
        );
    """)

    # Active memory stack tracking current location in the tree
    current_path_stack: List[str] = []
    records_to_insert = []

    with open(CSV_FILE_PATH, mode="r", encoding="utf-8") as f:
        # DictReader automatically honors encapsulating quotes for comma-separated items
        reader = csv.DictReader(f)

        for row in reader:
            raw_title = row.get("Title", "")
            code = row.get("Code", "").strip()
            class_kind = row.get("ClassKind", "").strip()

            if not raw_title:
                continue

            depth, clean_title = calculate_depth_and_clean_title(raw_title)

            # Adjust the contextual path stack dynamically based on active line depth
            if depth < len(current_path_stack):
                current_path_stack = current_path_stack[:depth]
            elif depth == len(current_path_stack):
                if current_path_stack:
                    current_path_stack.pop()

            current_path_stack.append(clean_title)

            # Synthesize the complete hierarchical context chain
            full_context_path = " > ".join(current_path_stack)

            # Filter Out Blocks and Placeholders: Only commit concrete actionable codes
            if code and code != "_NOCODEASSIGNED":
                records_to_insert.append((code, clean_title, class_kind, full_context_path))

    # Bulk insert all parsed records in a single transactional batch
    cursor.executemany(
        """
        INSERT INTO icd11_taxonomy (code, title, class_kind, context_path)
        VALUES (?, ?, ?, ?);
    """,
        records_to_insert,
    )

    # Build optimization indexes over the primary lookup columns
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_taxonomy_code ON icd11_taxonomy(code);")

    conn.commit()
    conn.close()
    print(f"🎉 Success! Ingested {len(records_to_insert)} functional diagnostic codes into SQLite.")


if __name__ == "__main__":
    seed_icd11_taxonomy()
