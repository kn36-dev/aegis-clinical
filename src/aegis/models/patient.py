# src/aegis/models/patient.py
from datetime import date
from enum import Enum
from uuid import UUID

from aegis.models.base import DomainModel, MedicalRecordNumber

# Patient
# Owns
# - patient_id
# - medical_record_number MRN
# - first_name
# - last_name
# - date_of_birth DOB

# Does not include
# - ICD suggestions
# - Workflow status
# - Embeddings


class BiologicalSex(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class Demographics(DomainModel):
    biological_sex: BiologicalSex
    ethnicity: str | None = None
    nationality: str | None = None


class Patient(DomainModel):
    """
    Canonical representation of a patient.

    This model represents only patient identity and demographics.
    It intentionally does NOT contain clinical information,
    diagnoses, workflow state, embeddings, or AI outputs.
    """

    patient_id: UUID
    medical_record_number: MedicalRecordNumber
    date_of_birth: date
    demographics: Demographics


# --------------------------------------
# How is it defined?

# from uuid import uuid4
# from datetime import date

# patient = Patient(
#     patient_id=uuid4(),
#     medical_record_number="MRN-2026-00123",
#     date_of_birth=date(1989, 4, 17),
#     demographics=Demographics(
#         biological_sex=BiologicalSex.MALE,
#         ethnicity="Chinese",
#         nationality="Malaysian",
#     ),
# )

# print(patient)

# --------------------------------------
# How is it serialized?

# json_data = patient.model_dump_json()

# restored = Patient.model_validate_json(json_data)

# assert restored == patient
