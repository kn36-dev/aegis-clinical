# This is good for testing the database after it is seeded
# Consider adding this to CI/CD during tests

import argparse
import sqlite3
from pathlib import Path


def verify_icd11_row(code: str) -> None:
    db_path = Path("data/clinical_registry.db")
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            code,
            title,
            class_kind,
            context_path,
            block_id,
            chapter_no,
            is_leaf,
            is_residual,
            grouping_1,
            grouping_2,
            grouping_3,
            grouping_4,
            grouping_5,
            foundation_uri,
            linearization_uri
        FROM icd11_taxonomy
        WHERE code = ?;
        """,
        (code,),
    )
    record = cursor.fetchone()
    conn.close()

    if record:
        print("✅ Database verification passed.")
        print(f"Code:             {record[0]}")
        print(f"Title:            {record[1]}")
        print(f"Class Kind:       {record[2]}")
        print(f"Context Path:     {record[3]}")
        print(f"Block ID:         {record[4]}")
        print(f"Chapter No:       {record[5]}")
        print(f"Is Leaf:          {record[6]}")
        print(f"Is Residual:      {record[7]}")
        print(f"Grouping 1:       {record[8]}")
        print(f"Grouping 2:       {record[9]}")
        print(f"Grouping 3:       {record[10]}")
        print(f"Grouping 4:       {record[11]}")
        print(f"Grouping 5:       {record[12]}")
        print(f"Foundation URI:   {record[13]}")
        print(f"Linearization URI:{record[14]}")
    else:
        print(f"❌ Verification failed: Code not found: {code}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify a specific ICD-11 taxonomy row")
    parser.add_argument("code", nargs="?", default="1A03.Z", help="ICD code to look up")
    args = parser.parse_args()

    verify_icd11_row(args.code)
