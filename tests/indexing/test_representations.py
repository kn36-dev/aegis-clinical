import pytest

from aegis.database.repositories.models import ICDTaxonomyRecord
from aegis.indexing.documents import RepresentationType
from aegis.indexing.representations.structured_prose import (
    StructuredProseRepresentation,
)


@pytest.fixture
def taxonomy_record() -> ICDTaxonomyRecord:
    return ICDTaxonomyRecord(
        code="1A00",
        title="Cholera",
        context_path=(
            "Gastroenteritis or colitis of infectious origin → "
            "Bacterial intestinal infections → "
            "Cholera"
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

    assert f"Clinical Term: {taxonomy_record.title}" in document.text


def test_contains_hierarchy(
    taxonomy_record: ICDTaxonomyRecord,
):
    strategy = StructuredProseRepresentation()

    document = strategy.build(taxonomy_record)

    assert "Classification Hierarchy:" in document.text
    assert "L1:" in document.text
    assert "Clinical Term:" in document.text


def test_title_strips_leading_dashes():
    strategy = StructuredProseRepresentation()
    record = ICDTaxonomyRecord(
        code="1A00",
        title="- - - Cholera",
        chapter_no="01",
    )

    document = strategy.build(record)

    assert document.concept_id == "1A00"
    assert "ICD-11 Code: 1A00" in document.text


def test_omits_irrelevant_metadata_from_embedding_text():
    strategy = StructuredProseRepresentation()
    record = ICDTaxonomyRecord(
        code="1A00",
        title="Cholera",
        chapter_no="01",
    )

    document = strategy.build(record)

    assert "Block:" not in document.text
    assert "Grouping" not in document.text
    assert "Chapter:" not in document.text


def test_metadata_contains_expected_fields(
    taxonomy_record: ICDTaxonomyRecord,
):
    strategy = StructuredProseRepresentation()

    document = strategy.build(taxonomy_record)

    assert document.metadata.code == taxonomy_record.code
    assert document.metadata.title == taxonomy_record.title
    assert document.metadata.context_path == taxonomy_record.context_path


def test_build_is_deterministic(
    taxonomy_record: ICDTaxonomyRecord,
):
    strategy = StructuredProseRepresentation()

    first = strategy.build(taxonomy_record)
    second = strategy.build(taxonomy_record)

    assert first == second


def test_context_path_with_arrow_separator_produces_hierarchy():
    strategy = StructuredProseRepresentation()
    record = ICDTaxonomyRecord(
        code="1A08",
        title="Paratyphoid fever",
        context_path=(
            "Gastroenteritis or colitis of infectious origin → "
            "Bacterial intestinal infections → "
            "Intestinal infections due to Salmonella → "
            "Paratyphoid fever"
        ),
    )

    document = strategy.build(record)

    assert "L1: Gastroenteritis or colitis of infectious origin" in document.text
    assert "L2: Bacterial intestinal infections" in document.text
    assert "L3: Intestinal infections due to Salmonella" in document.text


def test_context_path_with_gt_separator_produces_hierarchy():
    strategy = StructuredProseRepresentation()
    record = ICDTaxonomyRecord(
        code="1A08",
        title="Paratyphoid fever",
        context_path=(
            "Gastroenteritis or colitis of infectious origin > "
            "Bacterial intestinal infections > "
            "Intestinal infections due to Salmonella > "
            "Paratyphoid fever"
        ),
    )

    document = strategy.build(record)

    assert "L1: Gastroenteritis or colitis of infectious origin" in document.text
    assert "L2: Bacterial intestinal infections" in document.text
    assert "L3: Intestinal infections due to Salmonella" in document.text


def test_arrow_and_gt_separators_produce_identical_representation_text():
    strategy = StructuredProseRepresentation()
    arrow_record = ICDTaxonomyRecord(
        code="1A08",
        title="Paratyphoid fever",
        context_path=(
            "Gastroenteritis or colitis of infectious origin → "
            "Bacterial intestinal infections → "
            "Intestinal infections due to Salmonella → "
            "Paratyphoid fever"
        ),
    )
    gt_record = ICDTaxonomyRecord(
        code="1A08",
        title="Paratyphoid fever",
        context_path=(
            "Gastroenteritis or colitis of infectious origin > "
            "Bacterial intestinal infections > "
            "Intestinal infections due to Salmonella > "
            "Paratyphoid fever"
        ),
    )

    arrow_document = strategy.build(arrow_record)
    gt_document = strategy.build(gt_record)

    assert arrow_document.text == gt_document.text
