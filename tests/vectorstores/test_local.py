from aegis.indexing.documents import RepresentationDocument, RepresentationType, VectorDocument
from aegis.vectorstores.local import LocalVectorStore


def make_vector(concept_id: str) -> VectorDocument:
    representation = RepresentationDocument(
        concept_id=concept_id,
        representation_type=RepresentationType.STRUCTURED_PROSE,
        text="dummy text",
        metadata={},
    )

    return VectorDocument(
        representation=representation,
        embedding=[0.1, 0.2, 0.3],
    )


def test_index_many_stores_documents():
    store = LocalVectorStore()

    docs = [make_vector("A00"), make_vector("B00")]

    store.index_many(docs)

    assert store.get("A00") is not None
    assert store.get("B00") is not None


def test_upsert_overwrites():
    store = LocalVectorStore()

    d1 = make_vector("A00")
    d2 = make_vector("A00")

    store.upsert(d1)
    store.upsert(d2)

    assert store.get("A00") is d2
    assert store.count() == 1


def test_delete_removes():
    store = LocalVectorStore()

    doc = make_vector("A00")
    store.index(doc)

    store.delete("A00")

    assert store.get("A00") is None


def test_all_returns_all():
    store = LocalVectorStore()

    docs = [make_vector("A00"), make_vector("B00"), make_vector("C00")]

    store.index_many(docs)

    all_docs = store.all()

    assert len(all_docs) == 3
