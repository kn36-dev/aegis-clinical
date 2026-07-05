import csv
import re
import sqlite3
from typing import Any, List, Optional, Tuple

from aegis.database.repositories.icd_repository import ICDRepository
from aegis.database.repositories.models import ICDTaxonomyRecord

CSV_FILE_PATH = "data/smallerslice.csv"
DB_FILE_PATH = "data/clinical_registry.db"


# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------


def parse_bool(value: Optional[Any]) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v == "true":
            return True
        if v == "false":
            return False
    return None


def clean_title(title: str) -> str:
    return re.sub(r"^\s*(?:-\s*)+", "", title).strip()


# -----------------------------------------------------------------------------
# SEEDER
# -----------------------------------------------------------------------------


def seed_icd11_taxonomy():
    print("🛡️ Rebuilding ICD-11 taxonomy database...")

    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()

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

    # -----------------------------------------------------------------------------
    # STATE (FIXED: DUAL STACK MODEL)
    # -----------------------------------------------------------------------------

    block_stack: List[Tuple[int, str]] = []
    category_stack: List[Tuple[int, str]] = []

    records: List[ICDTaxonomyRecord] = []

    # -----------------------------------------------------------------------------
    # STREAM PROCESSING
    # -----------------------------------------------------------------------------

    with open(CSV_FILE_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            code = (row.get("Code") or "").strip()
            raw_title = row.get("Title") or ""
            title = clean_title(raw_title)

            class_kind = (row.get("ClassKind") or "").strip()
            depth = int(row.get("DepthInKind") or 0)
            block_id = row.get("BlockId")

            # ---------------------------------------------------------------------
            # CHAPTER SKIP (root structural container)
            # ---------------------------------------------------------------------
            if class_kind == "chapter":
                continue

            # ---------------------------------------------------------------------
            # BLOCK LOGIC
            # ---------------------------------------------------------------------
            if class_kind == "block":
                # blocks reset category context entirely
                category_stack = []

                # maintain block hierarchy using depth
                block_stack = [(d, t) for (d, t) in block_stack if d < depth]
                block_stack.append((depth, title))

                context_path = " → ".join(t for _, t in block_stack)

                print(f"[BLOCK] {code} depth={depth}")
                print("       ", context_path)

            # ---------------------------------------------------------------------
            # CATEGORY LOGIC
            # ---------------------------------------------------------------------
            else:
                # categories depend on BOTH:
                # - current block context
                # - category depth chain

                # reset category stack if block context is empty (safety guard)
                if not block_stack:
                    category_stack = []

                # maintain category hierarchy independently
                category_stack = [(d, t) for (d, t) in category_stack if d < depth]
                category_stack.append((depth, title))

                context_path = " → ".join(
                    [t for _, t in block_stack] + [t for _, t in category_stack]
                )

                print(f"[CAT] {code} depth={depth}")
                print("     ", context_path)

            # ---------------------------------------------------------------------
            # STORE RECORD
            # ---------------------------------------------------------------------
            if not code or not title or code == "_NOCODEASSIGNED":
                continue

            records.append(
                ICDTaxonomyRecord(
                    code=code,
                    title=title,
                    class_kind=class_kind,
                    context_path=context_path,
                    block_id=block_id,
                    chapter_no=row.get("ChapterNo"),
                    is_leaf=parse_bool(row.get("isLeaf")),
                    is_residual=parse_bool(row.get("IsResidual")),
                    foundation_uri=row.get("Foundation URI"),
                    linearization_uri=row.get("Linearization (release) URI"),
                )
            )

    # -----------------------------------------------------------------------------
    # PERSIST
    # -----------------------------------------------------------------------------

    repo = ICDRepository(conn)
    repo.bulk_insert(records)

    conn.commit()
    conn.close()

    print(f"✅ ICD-11 rebuilt successfully: {len(records)} records inserted")


if __name__ == "__main__":
    seed_icd11_taxonomy()
