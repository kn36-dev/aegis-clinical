from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from pydantic import BaseModel, Field

from aegis.database.connection import get_db_connection


class ClinicalMatchRecord(BaseModel):
    patient_id: str
    raw_notes: str
    clinical_notes_clear: str | None = None
    icd11_codes: list[str] = Field(default_factory=list)
    status: str = "PENDING_ANONYMIZATION"
    version: int = 1


class Icd11TaxonomyRecord(BaseModel):
    code: str
    title: str
    class_kind: str
    context_path: str


class ClinicalRegistryRepository:
    def __init__(self, db_path: str | Path | sqlite3.Connection):
        self.conn: sqlite3.Connection | None = None
        if isinstance(db_path, sqlite3.Connection):
            self.conn = db_path
        else:
            self.conn = self._connect(Path(db_path))
        self._ensure_schema()

    def _connect(self, db_path: Path) -> sqlite3.Connection:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _ensure_schema(self) -> None:
        if self.conn is None:
            raise RuntimeError("Repository connection is not initialized")
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS patient_identity_vault (
                patient_id TEXT PRIMARY KEY,
                medical_record_number TEXT UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                date_of_birth TEXT NOT NULL
            );
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS patient_case (
                patient_id TEXT PRIMARY KEY,
                case_id TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('pending_ai', 'pending_hitl', 'archived', 'failed')),
                ingress_timestamp TEXT NOT NULL,
                raw_clinical_note TEXT NOT NULL,
                anonymized_clinical_note TEXT,
                raw_notes TEXT,
                clinical_notes_clear TEXT,
                icd11_codes TEXT,
                version INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (patient_id) REFERENCES patient_identity_vault(patient_id)
            );
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS icd11_taxonomy_reference (
                code TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                class_kind TEXT NOT NULL,
                context_path TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def get_patient_case(self, patient_id: str) -> ClinicalMatchRecord | None:
        if self.conn is None:
            raise RuntimeError("Repository connection is not initialized")
        row = self.conn.execute(
            "SELECT patient_id, raw_notes, clinical_notes_clear, icd11_codes, status, version FROM patient_case WHERE patient_id = ?;",
            (patient_id,),
        ).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["icd11_codes"] = json.loads(data["icd11_codes"] or "[]")
        return ClinicalMatchRecord.model_validate(data)

    def upsert_patient_case(self, record: ClinicalMatchRecord) -> None:
        if self.conn is None:
            raise RuntimeError("Repository connection is not initialized")
        normalized_status = record.status.lower().replace("pending_anonymization", "pending_ai")
        self.conn.execute(
            """
            INSERT OR IGNORE INTO patient_identity_vault (
                patient_id,
                medical_record_number,
                first_name,
                last_name,
                date_of_birth
            ) VALUES (?, ?, ?, ?, ?);
            """,
            (record.patient_id, record.patient_id, "", "", ""),
        )
        self.conn.execute(
            """
            INSERT INTO patient_case (
                patient_id,
                case_id,
                status,
                ingress_timestamp,
                raw_clinical_note,
                anonymized_clinical_note,
                raw_notes,
                clinical_notes_clear,
                icd11_codes,
                version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(patient_id) DO UPDATE SET
                case_id = excluded.case_id,
                status = excluded.status,
                ingress_timestamp = excluded.ingress_timestamp,
                raw_clinical_note = excluded.raw_clinical_note,
                anonymized_clinical_note = excluded.anonymized_clinical_note,
                raw_notes = excluded.raw_notes,
                clinical_notes_clear = excluded.clinical_notes_clear,
                icd11_codes = excluded.icd11_codes,
                version = excluded.version;
            """,
            (
                record.patient_id,
                record.patient_id,
                normalized_status,
                "",
                record.raw_notes,
                record.clinical_notes_clear,
                record.raw_notes,
                record.clinical_notes_clear,
                json.dumps(record.icd11_codes),
                record.version,
            ),
        )
        self._commit_if_needed()

    def upsert_icd11_entry(self, entry: Icd11TaxonomyRecord) -> None:
        if self.conn is None:
            raise RuntimeError("Repository connection is not initialized")
        self.conn.execute(
            """
            INSERT INTO icd11_taxonomy_reference (code, title, class_kind, context_path)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                title = excluded.title,
                class_kind = excluded.class_kind,
                context_path = excluded.context_path;
            """,
            (entry.code, entry.title, entry.class_kind, entry.context_path),
        )
        self._commit_if_needed()

    def select_icd11_entry(self, code: str) -> Icd11TaxonomyRecord | None:
        if self.conn is None:
            raise RuntimeError("Repository connection is not initialized")
        row = self.conn.execute(
            "SELECT code, title, class_kind, context_path FROM icd11_taxonomy_reference WHERE code = ?;",
            (code,),
        ).fetchone()
        if row is None:
            return None
        return Icd11TaxonomyRecord.model_validate(dict(row))

    def _commit_if_needed(self) -> None:
        if self.conn is None:
            return
        if not self.conn.in_transaction:
            self.conn.commit()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        if self.conn is None:
            raise RuntimeError("Repository connection is not initialized")
        if not self.conn.in_transaction:
            self.conn.execute("BEGIN")
        try:
            yield
            if self.conn.in_transaction:
                self.conn.commit()
        except Exception:
            if self.conn.in_transaction:
                self.conn.rollback()
            raise

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None
