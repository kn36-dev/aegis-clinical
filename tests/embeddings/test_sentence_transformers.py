from aegis.embeddings.sentence_transformers import SentenceTransformersEmbeddingProvider
from aegis.indexing.documents import (
    RepresentationDocument,
    RepresentationMetadata,
    RepresentationType,
)


def make_provider():
    return SentenceTransformersEmbeddingProvider(model_name="BAAI/bge-base-en-v1.5")


def test_embedding_shape():
    doc = RepresentationDocument(
        concept_id="test",
        representation_type=RepresentationType.STRUCTURED_PROSE,
        text="diabetes mellitus",
        metadata=RepresentationMetadata(
            code="code",
            title="title",
            representation_type=RepresentationType.STRUCTURED_PROSE,
            embedded_text="",
        ),
    )
    provider = make_provider()
    result = provider.embed(doc)

    assert len(result.embedding) == provider._embedding_dim


def test_embed_many_returns_same_count():
    docs = [
        RepresentationDocument(
            concept_id=f"c{i}",
            representation_type=RepresentationType.STRUCTURED_PROSE,
            text=f"condition {i}",
            metadata=RepresentationMetadata(
                code="code",
                title="title",
                representation_type=RepresentationType.STRUCTURED_PROSE,
                embedded_text="",
            ),
        )
        for i in range(10)
    ]
    provider = make_provider()
    results = provider.embed_many(docs)

    assert len(results) == len(docs)


def test_embed_many_alignment():
    docs = [
        RepresentationDocument(
            concept_id="a",
            representation_type=RepresentationType.STRUCTURED_PROSE,
            text="hypertension",
            metadata=RepresentationMetadata(
                code="code",
                title="title",
                representation_type=RepresentationType.STRUCTURED_PROSE,
                embedded_text="",
            ),
        ),
        RepresentationDocument(
            concept_id="b",
            representation_type=RepresentationType.STRUCTURED_PROSE,
            text="diabetes",
            metadata=RepresentationMetadata(
                code="code",
                title="title",
                representation_type=RepresentationType.STRUCTURED_PROSE,
                embedded_text="",
            ),
        ),
    ]
    provider = make_provider()
    results = provider.embed_many(docs)

    assert results[0].representation.concept_id == "a"
    assert results[1].representation.concept_id == "b"


def test_embed_many_empty():
    provider = make_provider()
    assert provider.embed_many([]) == []


def test_embed_query_shape():
    provider = make_provider()

    embedding = provider.embed_query("diabetes mellitus")

    assert len(embedding) == provider._embedding_dim
