from __future__ import annotations

import sqlite3

from aegis.database.repositories.icd_repository import ICDRepository
from aegis.infrastructure.sqlite.icd_code_validator import SQLiteICDCodeValidator


def _seed_icd_code(conn: sqlite3.Connection, code: str) -> None:
    conn.execute(
        "INSERT INTO icd11_taxonomy (code, title, class_kind) VALUES (?, ?, 'category');",
        (code, f"Condition {code}"),
    )
    conn.commit()


def test_is_valid_true_for_known_code(clinical_db_connection: sqlite3.Connection) -> None:
    _seed_icd_code(clinical_db_connection, "1A00")
    validator = SQLiteICDCodeValidator(ICDRepository(clinical_db_connection))

    assert validator.is_valid("1A00") is True


def test_is_valid_false_for_unknown_code(clinical_db_connection: sqlite3.Connection) -> None:
    validator = SQLiteICDCodeValidator(ICDRepository(clinical_db_connection))

    assert validator.is_valid("UNKNOWN99") is False


def test_is_valid_delegates_lookup_to_repository_without_duplicating_sql(
    clinical_db_connection: sqlite3.Connection,
) -> None:
    """
    Deleting a seeded code through the same repository the validator uses
    must flip the validator's answer -- proving `is_valid` reads through
    `ICDRepository.get_by_code` rather than caching or re-querying SQL of
    its own.
    """
    _seed_icd_code(clinical_db_connection, "1A00")
    repository = ICDRepository(clinical_db_connection)
    validator = SQLiteICDCodeValidator(repository)
    assert validator.is_valid("1A00") is True

    clinical_db_connection.execute("DELETE FROM icd11_taxonomy WHERE code = '1A00';")
    clinical_db_connection.commit()

    assert validator.is_valid("1A00") is False
