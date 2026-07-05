# To prevent raw SQL in LangGraph nodes, we allow access through these centralized repositories
"""
ICD Taxonomy Repository

This layer is the ONLY component allowed to:
- read ICD taxonomy data from SQLite
- write ICD taxonomy data into SQLite
- translate SQLite rows → ICDTaxonomyRecord

It acts as the boundary between:
    SQLite schema
    and
    application-level indexing/domain logic
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3
from typing import Iterable, List, Optional

from aegis.database.repositories.models import ICDTaxonomyRecord

# ============================================================================
# ICD Repository
# ============================================================================


class ICDRepository:
    """
    Repository responsible for all ICD-11 taxonomy persistence operations.
    """

    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection

    # ------------------------------------------------------------------------
    # READ OPERATIONS
    # ------------------------------------------------------------------------

    def get_by_code(self, code: str) -> Optional[ICDTaxonomyRecord]:
        """
        Fetch a single ICD record by code.
        """

        cursor = self._conn.cursor()
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

        row = cursor.fetchone()
        if not row:
            return None

        return self._row_to_record(row)

    def list_all(self, limit: Optional[int] = None) -> List[ICDTaxonomyRecord]:
        """
        Fetch all ICD records (optionally limited).
        """

        cursor = self._conn.cursor()

        query = """
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
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)

        return [self._row_to_record(row) for row in cursor.fetchall()]

    # ------------------------------------------------------------------------
    # WRITE OPERATIONS (used by seed pipeline, not runtime)
    # ------------------------------------------------------------------------

    def bulk_insert(self, records: Iterable[ICDTaxonomyRecord]) -> None:
        """
        Bulk insert ICD taxonomy records.

        This is used only during ingestion / seeding.
        """

        cursor = self._conn.cursor()

        cursor.executemany(
            """
            INSERT INTO icd11_taxonomy (
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
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            [
                (
                    r.code,
                    r.title,
                    r.class_kind,
                    r.context_path,
                    r.block_id,
                    r.chapter_no,
                    r.is_leaf,
                    r.is_residual,
                    r.grouping_1,
                    r.grouping_2,
                    r.grouping_3,
                    r.grouping_4,
                    r.grouping_5,
                    r.foundation_uri,
                    r.linearization_uri,
                )
                for r in records
            ],
        )
        self._conn.commit()

    # ------------------------------------------------------------------------
    # INTERNAL MAPPING
    # ------------------------------------------------------------------------

    def _row_to_record(self, row: tuple) -> ICDTaxonomyRecord:
        """
        Maps SQLite row → ICDTaxonomyRecord
        """

        return ICDTaxonomyRecord(
            code=row[0],
            title=row[1],
            class_kind=row[2],
            context_path=row[3],
            block_id=row[4],
            chapter_no=row[5],
            is_leaf=row[6],
            is_residual=row[7],
            grouping_1=row[8],
            grouping_2=row[9],
            grouping_3=row[10],
            grouping_4=row[11],
            grouping_5=row[12],
            foundation_uri=row[13],
            linearization_uri=row[14],
        )
