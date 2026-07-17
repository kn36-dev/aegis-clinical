import pytest
from pydantic import ValidationError

from aegis.indexing.documents import (
    RepresentationDocument,
    RepresentationMetadata,
    RepresentationType,
    VectorDocument,
)


def test_representation_document_creation():
    doc = RepresentationDocument(
        concept_id="1A03.Z",
        representation_type=RepresentationType.STRUCTURED_PROSE,
        text="ICD-11 Code: 1A03.Z\nTitle: E. coli infection",
        metadata=RepresentationMetadata(
            code="icd",
            title="title",
            representation_type=RepresentationType.STRUCTURED_PROSE,
            embedded_text="",
        ),
    )

    assert doc.concept_id == "1A03.Z"
    assert doc.representation_type == RepresentationType.STRUCTURED_PROSE
    assert "E. coli" in doc.text
    assert doc.metadata.code == "icd"


def test_representation_document_immutable():
    doc = RepresentationDocument(
        concept_id="1A03",
        representation_type=RepresentationType.STRUCTURED_PROSE,
        text="test",
        metadata=RepresentationMetadata(
            code="code",
            title="title",
            representation_type=RepresentationType.STRUCTURED_PROSE,
            embedded_text="",
        ),
    )

    with pytest.raises(ValidationError):
        doc.text = "modified"


def test_vector_document_wraps_representation():
    rep = RepresentationDocument(
        concept_id="1A03",
        representation_type=RepresentationType.STRUCTURED_PROSE,
        text="ICD concept text",
        metadata=RepresentationMetadata(
            code="code",
            title="title",
            representation_type=RepresentationType.STRUCTURED_PROSE,
            embedded_text="",
        ),
    )

    vector = VectorDocument(representation=rep, embedding=[0.1, 0.2, 0.3])

    assert vector.representation.concept_id == "1A03"
    assert vector.embedding == [0.1, 0.2, 0.3]


def test_vector_document_preserves_provenance():
    rep = RepresentationDocument(
        concept_id="1A03.Z",
        representation_type=RepresentationType.STRUCTURED_PROSE,
        text="some text",
        metadata=RepresentationMetadata(
            code="code",
            title="title",
            representation_type=RepresentationType.STRUCTURED_PROSE,
            embedded_text="",
            chapter_number="A00-B99",
        ),
    )

    vector = VectorDocument(representation=rep, embedding=[0.9, 0.8])

    assert vector.representation.metadata.chapter_number == "A00-B99"
