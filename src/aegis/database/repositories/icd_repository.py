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
        select_columns = self._get_select_columns()
        if not select_columns:
            return None

        cursor.execute(
            f"SELECT {', '.join(select_columns)} FROM icd11_taxonomy WHERE code = ?;",
            (code,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        return self._row_to_record(row, select_columns)

    def list_all(self, limit: Optional[int] = None) -> List[ICDTaxonomyRecord]:
        """
        Fetch all ICD records (optionally limited).
        """

        cursor = self._conn.cursor()
        select_columns = self._get_select_columns()
        if not select_columns:
            return []

        query = f"SELECT {', '.join(select_columns)} FROM icd11_taxonomy"

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)

        return [self._row_to_record(row, select_columns) for row in cursor.fetchall()]

    # ------------------------------------------------------------------------
    # WRITE OPERATIONS (used by seed pipeline, not runtime)
    # ------------------------------------------------------------------------

    def bulk_insert(self, records: Iterable[ICDTaxonomyRecord]) -> None:
        """
        Bulk insert ICD taxonomy records.

        This is used only during ingestion / seeding.
        """

        cursor = self._conn.cursor()
        insert_columns = self._get_insert_columns()
        if not insert_columns:
            return

        placeholders = ", ".join("?" for _ in insert_columns)
        query = f"INSERT INTO icd11_taxonomy ({', '.join(insert_columns)}) VALUES ({placeholders});"

        rows = []
        for record in records:
            values = []
            for column in insert_columns:
                if column == "code":
                    values.append(record.code)
                elif column == "title":
                    values.append(record.title)
                elif column == "context_path":
                    values.append(record.context_path)
                elif column == "chapter_no":
                    values.append(record.chapter_no)
                elif column == "is_leaf":
                    values.append(self._coerce_bool(record.is_leaf))
                elif column == "is_residual":
                    values.append(self._coerce_bool(record.is_residual))
                else:
                    values.append(None)
            rows.append(tuple(values))

        cursor.executemany(query, rows)
        self._conn.commit()

    # ------------------------------------------------------------------------
    # INTERNAL MAPPING
    # ------------------------------------------------------------------------

    def _get_select_columns(self) -> List[str]:
        available_columns = self._get_available_columns()
        return [
            column
            for column in (
                "code",
                "title",
                "context_path",
                "chapter_no",
                "is_leaf",
                "is_residual",
            )
            if column in available_columns
        ]

    def _get_insert_columns(self) -> List[str]:
        available_columns = self._get_available_columns()
        return [
            column
            for column in (
                "code",
                "title",
                "context_path",
                "chapter_no",
                "is_leaf",
                "is_residual",
            )
            if column in available_columns
        ]

    def _get_available_columns(self) -> List[str]:
        cursor = self._conn.execute("PRAGMA table_info(icd11_taxonomy)")
        rows = cursor.fetchall()
        return [row[1] for row in rows]

    def _coerce_bool(self, value: Optional[bool]) -> Optional[int]:
        if value is None:
            return None
        return int(value)

    def _row_to_record(self, row: tuple, selected_columns: List[str]) -> ICDTaxonomyRecord:
        """
        Maps SQLite row → ICDTaxonomyRecord
        """

        values = {column: row[index] for index, column in enumerate(selected_columns)}

        return ICDTaxonomyRecord(
            code=values.get("code") or "",
            title=values.get("title") or "",
            context_path=values.get("context_path"),
            chapter_no=values.get("chapter_no"),
            is_leaf=self._coerce_optional_bool(values.get("is_leaf")),
            is_residual=self._coerce_optional_bool(values.get("is_residual")),
        )

    def _coerce_optional_bool(self, value: object) -> Optional[bool]:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "y"}:
                return True
            if normalized in {"0", "false", "no", "n"}:
                return False
        return None
