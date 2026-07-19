from aegis.indexing.documents import (
    RepresentationDocument,
    RepresentationMetadata,
    RepresentationType,
    VectorDocument,
)
from aegis.retrieval.providers.local import LocalVectorQueryProvider
from aegis.vectorstores.local import LocalVectorStore


def make_vector(concept_id: str, embedding: list[float], code: str | None = None) -> VectorDocument:
    representation = RepresentationDocument(
        concept_id=concept_id,
        representation_type=RepresentationType.STRUCTURED_PROSE,
        text="dummy text",
        metadata=RepresentationMetadata(
            code=code or concept_id,
            title=f"Title for {concept_id}",
            representation_type=RepresentationType.STRUCTURED_PROSE,
            embedded_text="",
        ),
    )
    return VectorDocument(representation=representation, embedding=embedding)


class TestLocalVectorQueryProvider:
    def test_ranks_by_cosine_similarity_descending(self):
        store = LocalVectorStore()
        store.index_many(
            [
                make_vector("A", [1.0, 0.0]),
                make_vector("B", [0.0, 1.0]),
                make_vector("C", [0.9, 0.1]),
            ]
        )
        provider = LocalVectorQueryProvider(store)

        matches = provider.query(embedding=[1.0, 0.0], top_k=3)

        assert [match.id for match in matches] == ["A", "C", "B"]

    def test_respects_top_k(self):
        store = LocalVectorStore()
        store.index_many([make_vector("A", [1.0, 0.0]), make_vector("B", [0.0, 1.0])])
        provider = LocalVectorQueryProvider(store)

        matches = provider.query(embedding=[1.0, 0.0], top_k=1)

        assert len(matches) == 1
        assert matches[0].id == "A"

    def test_translates_metadata_from_representation(self):
        store = LocalVectorStore()
        store.index(make_vector("A", [1.0, 0.0], code="ME05.1"))
        provider = LocalVectorQueryProvider(store)

        matches = provider.query(embedding=[1.0, 0.0], top_k=1)

        assert matches[0].metadata["code"] == "ME05.1"

    def test_empty_store_returns_no_matches(self):
        provider = LocalVectorQueryProvider(LocalVectorStore())

        assert provider.query(embedding=[1.0, 0.0], top_k=5) == []

    def test_zero_vector_does_not_raise_division_by_zero(self):
        store = LocalVectorStore()
        store.index(make_vector("A", [0.0, 0.0]))
        provider = LocalVectorQueryProvider(store)

        matches = provider.query(embedding=[1.0, 0.0], top_k=1)

        assert matches[0].score == 0.0
