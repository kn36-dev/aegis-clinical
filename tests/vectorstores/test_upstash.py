from unittest.mock import patch

from aegis.indexing.documents import (
    RepresentationDocument,
    RepresentationType,
    VectorDocument,
)
from aegis.vectorstores.upstash import UpstashVectorStore


def make_vector() -> VectorDocument:
    return VectorDocument(
        representation=RepresentationDocument(
            concept_id="1A03.Z",
            representation_type=RepresentationType.STRUCTURED_PROSE,
            text="Example",
            metadata={"code": "1A03.Z"},
        ),
        embedding=[0.1, 0.2, 0.3],
    )


@patch("aegis.vectorstores.upstash.Index")
def test_upsert_calls_sdk(mock_index):

    store = UpstashVectorStore(
        url="url",
        token="token",
    )

    vector = make_vector()

    store.index(vector)

    mock_index.return_value.upsert.assert_called_once()


@patch("aegis.vectorstores.upstash.Index")
def test_upsert_many_calls_sdk(mock_index):

    store = UpstashVectorStore(
        url="url",
        token="token",
    )

    vectors = [
        make_vector(),
        make_vector(),
    ]

    store.index_many(vectors)

    mock_index.return_value.upsert.assert_called_once()


@patch("aegis.vectorstores.upstash.Index")
def test_delete_calls_sdk(mock_index):

    store = UpstashVectorStore(
        url="url",
        token="token",
    )

    store.delete("1A03.Z")

    mock_index.return_value.delete.assert_called_once_with(ids=["1A03.Z"])
