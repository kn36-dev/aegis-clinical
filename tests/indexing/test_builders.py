import pytest

from aegis.database.repositories.models import ICDTaxonomyRecord
from aegis.indexing.builders import RepresentationBuilder
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
        context_path=("Certain infectious diseases > Bacterial intestinal infections"),
    )


@pytest.fixture
def builder() -> RepresentationBuilder:
    return RepresentationBuilder(
        strategy=StructuredProseRepresentation(),
    )


def test_builder_uses_configured_strategy(
    builder: RepresentationBuilder,
):
    assert builder.strategy.representation_type == RepresentationType.STRUCTURED_PROSE


def test_builder_builds_document(
    builder: RepresentationBuilder,
    taxonomy_record: ICDTaxonomyRecord,
):
    document = builder.build(taxonomy_record)

    assert document.concept_id == taxonomy_record.code
    assert taxonomy_record.title in document.text


def test_builder_build_many(
    builder: RepresentationBuilder,
):
    records = [
        ICDTaxonomyRecord(
            code="1A00",
            title="Cholera",
            class_kind="category",
        ),
        ICDTaxonomyRecord(
            code="1A01",
            title="Intestinal infection due to other Vibrio",
            class_kind="category",
        ),
    ]

    documents = builder.build_many(records)

    assert len(documents) == 2
    assert documents[0].concept_id == "1A00"
    assert documents[1].concept_id == "1A01"


def test_builder_is_deterministic(
    builder: RepresentationBuilder,
    taxonomy_record: ICDTaxonomyRecord,
):
    first = builder.build(taxonomy_record)
    second = builder.build(taxonomy_record)

    assert first == second
