"""
SQLiteICDCodeValidator

Concrete ``ICDCodeValidator`` adapter (``aegis.services.clinical_decision_service``)
backed by the canonical ICD-11 taxonomy in SQLite.

Delegates existence lookup entirely to ``ICDRepository``
(``aegis.database.repositories.icd_repository``) -- the only component
allowed to read/write ICD taxonomy data, per that module's own
docstring. No taxonomy SQL is duplicated here.

Answers only "does this code exist in the canonical taxonomy?". It
performs no fuzzy matching, synonym lookup, semantic retrieval, or code
suggestion -- those belong to retrieval/reasoning, not to this
read-only, deterministic validity check.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aegis.database.repositories.icd_repository import ICDRepository


class SQLiteICDCodeValidator:
    """
    ``ICDCodeValidator`` implementation backed by the ``icd11_taxonomy`` table.

    Structurally satisfies
    ``aegis.services.clinical_decision_service.ICDCodeValidator``
    (``is_valid``). Read-only and deterministic: the same taxonomy
    snapshot always produces the same answer for a given code.
    """

    def __init__(self, icd_repository: ICDRepository) -> None:
        self._icd_repository = icd_repository

    def is_valid(self, icd_code: str) -> bool:
        return self._icd_repository.get_by_code(icd_code) is not None
