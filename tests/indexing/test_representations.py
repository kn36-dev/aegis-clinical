import pytest

from aegis.database.repositories.models import ICDTaxonomyRecord
from aegis.indexing.documents import RepresentationType
from aegis.indexing.representations.structured_prose import (
    StructuredProseRepresentation,
)


@pytest.fixture
def taxonomy_record() -> ICDTaxonomyRecord:
    return ICDTaxonomyRecord(
        code="1A03.Z",
        title="Intestinal infections due to Escherichia coli, unspecified",
        class_kind="category",
        context_path=(
            "Certain infectious or parasitic diseases > "
            "Bacterial intestinal infections > "
            "Intestinal infections due to Escherichia coli"
        ),
    )


def test_returns_representation_document(
    taxonomy_record: ICDTaxonomyRecord,
):
    strategy = StructuredProseRepresentation()

    document = strategy.build(taxonomy_record)

    assert document.concept_id == taxonomy_record.code
    assert document.representation_type == RepresentationType.STRUCTURED_PROSE


def test_contains_code(
    taxonomy_record: ICDTaxonomyRecord,
):
    strategy = StructuredProseRepresentation()

    document = strategy.build(taxonomy_record)

    assert f"ICD-11 Code: {taxonomy_record.code}" in document.text


def test_contains_title(
    taxonomy_record: ICDTaxonomyRecord,
):
    strategy = StructuredProseRepresentation()

    document = strategy.build(taxonomy_record)

    assert taxonomy_record.title in document.text


def test_contains_hierarchy(
    taxonomy_record: ICDTaxonomyRecord,
):
    strategy = StructuredProseRepresentation()

    document = strategy.build(taxonomy_record)

    assert taxonomy_record.context_path is not None
    assert taxonomy_record.context_path in document.text


def test_contains_classification(
    taxonomy_record: ICDTaxonomyRecord,
):
    strategy = StructuredProseRepresentation()

    document = strategy.build(taxonomy_record)

    assert taxonomy_record.class_kind in document.text


def test_title_strips_leading_dashes():
    strategy = StructuredProseRepresentation()
    record = ICDTaxonomyRecord(
        code="1A00",
        title="- - - Cholera",
        class_kind="category",
        block_id="1A0",
        chapter_no="01",
    )

    document = strategy.build(record)

    assert "Cholera" in document.text
    assert "- - - Cholera" not in document.text


def test_contains_block_and_chapter_details():
    strategy = StructuredProseRepresentation()
    record = ICDTaxonomyRecord(
        code="1A00",
        title="Cholera",
        class_kind="category",
        block_id="1A0",
        chapter_no="01",
    )

    document = strategy.build(record)

    assert "Block: 1A0" in document.text
    assert "Chapter: 01" in document.text


def test_metadata_contains_expected_fields(
    taxonomy_record: ICDTaxonomyRecord,
):
    strategy = StructuredProseRepresentation()

    document = strategy.build(taxonomy_record)

    assert document.metadata["code"] == taxonomy_record.code
    assert document.metadata["title"] == taxonomy_record.title
    assert document.metadata["class_kind"] == taxonomy_record.class_kind


def test_build_is_deterministic(
    taxonomy_record: ICDTaxonomyRecord,
):
    strategy = StructuredProseRepresentation()

    first = strategy.build(taxonomy_record)
    second = strategy.build(taxonomy_record)

    assert first == second
