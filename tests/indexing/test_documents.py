from aegis.indexing.documents import (
    RepresentationDocument,
    RepresentationType,
    VectorDocument,
)


def test_representation_document_creation():
    doc = RepresentationDocument(
        concept_id="1A03.Z",
        representation_type=RepresentationType.STRUCTURED_PROSE,
        text="ICD-11 Code: 1A03.Z\nTitle: E. coli infection",
        metadata={"source": "icd"},
    )

    assert doc.concept_id == "1A03.Z"
    assert doc.representation_type == RepresentationType.STRUCTURED_PROSE
    assert "E. coli" in doc.text
    assert doc.metadata["source"] == "icd"


def test_representation_document_immutable():
    doc = RepresentationDocument(
        concept_id="1A03", representation_type=RepresentationType.STRUCTURED_PROSE, text="test"
    )

    try:
        doc.text = "modified"
        assert False
    except Exception:
        assert True


def test_vector_document_wraps_representation():
    rep = RepresentationDocument(
        concept_id="1A03",
        representation_type=RepresentationType.STRUCTURED_PROSE,
        text="ICD concept text",
    )

    vector = VectorDocument(representation=rep, embedding=[0.1, 0.2, 0.3])

    assert vector.representation.concept_id == "1A03"
    assert vector.embedding == [0.1, 0.2, 0.3]


def test_vector_document_preserves_provenance():
    rep = RepresentationDocument(
        concept_id="1A03.Z",
        representation_type=RepresentationType.STRUCTURED_PROSE,
        text="some text",
        metadata={"chapter": "A00-B99"},
    )

    vector = VectorDocument(representation=rep, embedding=[0.9, 0.8])

    assert vector.representation.metadata["chapter"] == "A00-B99"
