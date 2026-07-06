import csv
import sqlite3
from pathlib import Path

from aegis.database.repositories.icd_repository import ICDRepository
from aegis.database.seeds import seed_icd11


def test_seed_icd11_uses_taxonomy_table_and_supported_columns(tmp_path: Path) -> None:
    db_path = tmp_path / "clinical.db"
    csv_path = tmp_path / "taxonomy.csv"

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["Code", "Title", "ClassKind", "ChapterNo", "isLeaf", "IsResidual"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "Code": "A00",
                "Title": "Cholera",
                "ClassKind": "category",
                "ChapterNo": "01",
                "isLeaf": "true",
                "IsResidual": "false",
            }
        )

    inserted_count = seed_icd11(db_path=db_path, csv_path=csv_path)

    assert inserted_count == 1

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT code, title, class_kind, context_path, chapter_no, is_leaf, is_residual
            FROM icd11_taxonomy
            WHERE code = ?
            """,
            ("A00",),
        ).fetchone()

    assert row is not None
    assert row[1] == "Cholera"
    assert row[4] == "01"
    assert row[5] == 1
    assert row[6] == 0

    with sqlite3.connect(db_path) as conn:
        repo = ICDRepository(conn)
        record = repo.get_by_code("A00")

    assert record is not None
    assert record.chapter_no == "01"
    assert record.is_leaf is True
    assert record.is_residual is False
