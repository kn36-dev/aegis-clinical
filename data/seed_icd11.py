import csv
import os
import sqlite3
from typing import Any, List, Optional

from aegis.database.repositories.icd_repository import ICDRepository
from aegis.database.repositories.models import ICDTaxonomyRecord

CSV_FILE_PATH = "data/icd11_mms_simplified.csv"
DB_FILE_PATH = "data/clinical_registry.db"


def parse_bool(value: Optional[Any]) -> Optional[bool]:
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return bool(value)

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False

    return None


def clean_title(title: str) -> str:
    import re

    title = re.sub(r"^\s*(?:-\s*)+", "", title)
    return title.strip()


def seed_icd11_taxonomy():
    stack = []  # (depth, title)
    print("🛡️ Rebuilding ICD-11 taxonomy database...")

    if not os.path.exists(CSV_FILE_PATH):
        raise FileNotFoundError(f"Missing: {CSV_FILE_PATH}")

    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()

    # ----------------------------
    # RESET SCHEMA (source of truth)
    # ----------------------------
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

    records: List[ICDTaxonomyRecord] = []

    with open(CSV_FILE_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            code = (row.get("Code") or "").strip()
            raw_title = row.get("Title") or ""
            title = clean_title(raw_title)
            visual_depth = len(raw_title) - len(raw_title.lstrip("- "))
            depth = max(int(row.get("DepthInKind") or 0), visual_depth)
            class_kind = (row.get("ClassKind") or "").strip()

            if not title:
                continue

            # skip rows without real ICD codes if needed
            if not code or code == "_NOCODEASSIGNED":
                continue

            while stack and stack[-1][0] >= depth:
                stack.pop()

            parent_path = [x[1] for x in stack]
            context_path = " → ".join(parent_path + [title]) if parent_path else title

            stack.append((depth, title))

            record = ICDTaxonomyRecord(
                code=code,
                title=title,
                class_kind=class_kind,
                context_path=context_path,
                block_id=row.get("BlockId"),
                chapter_no=row.get("ChapterNo"),
                is_leaf=parse_bool(row.get("isLeaf")),
                is_residual=parse_bool(row.get("IsResidual")),
                grouping_1=row.get("Grouping1"),
                grouping_2=row.get("Grouping2"),
                grouping_3=row.get("Grouping3"),
                grouping_4=row.get("Grouping4"),
                grouping_5=row.get("Grouping5"),
                foundation_uri=row.get("Foundation URI"),
                linearization_uri=row.get("Linearization (release) URI"),
            )

            records.append(record)

    repo = ICDRepository(conn)
    repo.bulk_insert(records)

    conn.commit()
    conn.close()

    print(f"✅ ICD-11 rebuilt successfully: {len(records)} records inserted")


if __name__ == "__main__":
    seed_icd11_taxonomy()
