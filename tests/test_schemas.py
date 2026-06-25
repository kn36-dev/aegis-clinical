# tests/test_schemas.py

import sqlite3
from typing import Dict

import pytest

# These schemas will be refactored eventually when we have a cohesively
# structured database
CLINICAL_TABLE_SCHEMAS: Dict[str, str] = {
    "Patient_identity_vault": """
        CREATE TABLE IF NOT EXISTS Patient_identity_vault (
            patient_id TEXT PRIMARY KEY,
            medical_record_number TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            date_of_birth DATE NOT NULL
        );
    """,
    "Patient_cases": """
        CREATE TABLE IF NOT EXISTS Patient_cases (
            case_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('pending_ai', 'pending_hitl', 'archived', 'failed')),
            ingress_timestamp TEXT NOT NULL,
            raw_clinical_note TEXT NOT NULL,
            anonymized_clinical_note TEXT,
            FOREIGN KEY (patient_id) REFERENCES Patient_identity_vault(patient_id)
        );
    """,
    "ICD11_taxonomy_reference": """
        CREATE TABLE IF NOT EXISTS ICD11_taxonomy_reference (
            icd11_code TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            hierarchical_path TEXT NOT NULL,
            description TEXT
        );
    """,
    "Patient_extracted_codes": """
        CREATE TABLE IF NOT EXISTS Patient_extracted_codes (
            case_id TEXT NOT NULL,
            icd11_code TEXT NOT NULL,
            confidence_score REAL NOT NULL CHECK (confidence_score BETWEEN 0.0 AND 1.0),
            extraction_source TEXT NOT NULL,
            PRIMARY KEY (case_id, icd11_code),
            FOREIGN KEY (case_id) REFERENCES Patient_cases(case_id) ON DELETE CASCADE,
            FOREIGN KEY (icd11_code) REFERENCES ICD11_taxonomy_reference(icd11_code)
        );
    """,
    "Clinical_trial": """
        CREATE TABLE IF NOT EXISTS Clinical_trial (
            trial_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            phase TEXT NOT NULL CHECK (phase IN ('Phase 1', 'Phase 2', 'Phase 3', 'Phase 4')),
            sponsor TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('Recruiting', 'Completed', 'Suspended')),
            raw_eligibility_criteria TEXT NOT NULL
        );
    """,
    "Trial_Target_codes": """
        CREATE TABLE IF NOT EXISTS Trial_Target_codes (
            trial_id TEXT NOT NULL,
            icd11_code TEXT NOT NULL,
            criterion_type TEXT NOT NULL CHECK (criterion_type IN ('INCLUSION', 'EXCLUSION')),
            PRIMARY KEY (trial_id, icd11_code),
            FOREIGN KEY (trial_id) REFERENCES Clinical_trial(trial_id) ON DELETE CASCADE,
            FOREIGN KEY (icd11_code) REFERENCES ICD11_taxonomy_reference(icd11_code)
        );
    """,
    "Trial_Matches": """
        CREATE TABLE IF NOT EXISTS Trial_Matches (
            match_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            trigger_case_id TEXT NOT NULL,
            trial_id TEXT NOT NULL,
            structural_match_score REAL NOT NULL,
            match_status TEXT NOT NULL CHECK (match_status IN ('PENDING_REVIEW', 'PHYSICIAN_APPROVED', 'PHYSICIAN_REJECTED')),
            justification_summary TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES Patient_identity_vault(patient_id),
            FOREIGN KEY (trigger_case_id) REFERENCES Patient_cases(case_id) ON DELETE CASCADE,
            FOREIGN KEY (trial_id) REFERENCES Clinical_trial(trial_id) ON DELETE CASCADE
        );
    """,
    "Human_Review_Logs": """
        CREATE TABLE IF NOT EXISTS Human_Review_Logs (
            review_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            reviewer_badge_id TEXT NOT NULL,
            action_taken TEXT NOT NULL CHECK (action_taken IN ('APPROVED_ALL', 'OVERRIDDEN_AND_APPROVED', 'REJECTED_CASE')),
            physician_notes TEXT,
            cryptographic_signature TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (case_id) REFERENCES Patient_cases(case_id)
        );
    """,
}

GRAPH_TABLE_SCHEMAS: Dict[str, str] = {
    "checkpoint_blob": """
        CREATE TABLE IF NOT EXISTS checkpoint_blob (
            thread_id TEXT NOT NULL,
            checkpoint_id TEXT NOT NULL,
            parent_id TEXT,
            checkpoint BLOB NOT NULL,
            metadata BLOB NOT NULL,
            PRIMARY KEY (thread_id, checkpoint_id)
        );
    """
}


@pytest.fixture
def memory_db():
    """Provides a fresh, isolated in-memory DB connection per test case."""
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON;")
    yield connection
    connection.close()


def test_patient_identity_vault_schema(memory_db):
    """Validates that the decoupled Patient_identity_vault DDL is fully valid syntactically."""
    cursor = memory_db.cursor()

    # Extract isolated DDL string from registry dictionary
    vault_ddl = CLINICAL_TABLE_SCHEMAS["Patient_identity_vault"]

    # Execute single table compilation in complete isolation
    cursor.execute(vault_ddl)

    # Insert structured test seed row
    cursor.execute("""
        INSERT INTO Patient_identity_vault (patient_id, medical_record_number, first_name, last_name, date_of_birth)
        VALUES ('pt-100', 'MRN-999-888', 'John', 'Doe', '1990-01-01');
    """)
    memory_db.commit()

    # Test unique constraint failure assertion
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("""
            INSERT INTO Patient_identity_vault (patient_id, medical_record_number, first_name, last_name, date_of_birth)
            VALUES ('pt-200', 'MRN-999-888', 'Jane', 'Smith', '1992-05-12'); 
            -- Duplicated MRN must throw an IntegrityError exception
        """)
