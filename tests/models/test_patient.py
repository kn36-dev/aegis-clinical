from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegis.models.patient import (
    BiologicalSex,
    Demographics,
    Patient,
)


@pytest.fixture
def demographics():
    return Demographics(
        biological_sex=BiologicalSex.MALE,
        ethnicity="Chinese",
        nationality="Malaysian",
    )


def test_patient_construction(demographics):
    patient = Patient(
        patient_id=uuid4(),
        medical_record_number="MRN-0001",
        date_of_birth=date(1990, 5, 17),
        demographics=demographics,
    )

    assert patient.medical_record_number == "MRN-0001"
    assert patient.demographics.biological_sex == BiologicalSex.MALE


def test_patient_requires_mrn(demographics):
    with pytest.raises(ValidationError):
        Patient.model_validate(
            {
                "patient_id": uuid4(),
                "date_of_birth": date(1990, 5, 17),
                "demographics": demographics,
            }
        )


def test_patient_rejects_empty_mrn(demographics):
    with pytest.raises(ValidationError):
        Patient(
            patient_id=uuid4(),
            medical_record_number="",
            date_of_birth=date(1990, 5, 17),
            demographics=demographics,
        )


def test_patient_is_immutable(demographics):
    patient = Patient(
        patient_id=uuid4(),
        medical_record_number="MRN-0001",
        date_of_birth=date(1990, 5, 17),
        demographics=demographics,
    )

    with pytest.raises(ValidationError):
        patient.medical_record_number = "MRN-9999"


def test_patient_serialization_round_trip(demographics):
    patient = Patient(
        patient_id=uuid4(),
        medical_record_number="MRN-0001",
        date_of_birth=date(1990, 5, 17),
        demographics=demographics,
    )

    dumped = patient.model_dump()

    restored = Patient.model_validate(dumped)

    assert restored == patient


def test_patient_json_round_trip(demographics):
    patient = Patient(
        patient_id=uuid4(),
        medical_record_number="MRN-0001",
        date_of_birth=date(1990, 5, 17),
        demographics=demographics,
    )

    json_data = patient.model_dump_json()

    restored = Patient.model_validate_json(json_data)

    assert restored == patient
