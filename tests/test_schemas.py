# tests/test_schemas.py

import sqlite3

import pytest

from aegis.database.database import CLINICAL_TABLE_SCHEMAS


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
