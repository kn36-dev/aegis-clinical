# src/aegis/models/base.py
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class DomainModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=False,
        str_strip_whitespace=True,
    )


MedicalRecordNumber = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=50,
    ),
]

ClinicalText = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=50_000,
        strip_whitespace=True,
    ),
]

ICDCode = Annotated[
    str,
    StringConstraints(
        min_length=3,
        max_length=10,
        strip_whitespace=True,
    ),
]
