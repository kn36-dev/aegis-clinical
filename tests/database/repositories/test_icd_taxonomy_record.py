from dataclasses import FrozenInstanceError

import pytest

from aegis.database.repositories.models import ICDTaxonomyRecord


def test_icd_taxonomy_record_minimal_creation():
    record = ICDTaxonomyRecord(
        code="1A03.Z",
        title="Intestinal infections due to E. coli",
        context_path="A > B > C",
    )

    assert record.code == "1A03.Z"
    assert record.title == "Intestinal infections due to E. coli"
    assert record.context_path is not None
    assert record.context_path.startswith("A")


def test_icd_taxonomy_record_immutability():
    record = ICDTaxonomyRecord(
        code="1A03",
        title="Test",
    )

    # Context manager elegantly handles expected exceptions
    with pytest.raises(
        FrozenInstanceError
    ):  # Best practice: replace 'Exception' with your specific error class
        record.title = "Modified"  # type: ignore
        pass
