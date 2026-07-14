from unittest.mock import MagicMock, patch

from aegis.retrieval.providers.upstash import UpstashVectorQueryProvider


@patch("aegis.retrieval.providers.upstash.Index")
def test_query_calls_sdk_with_embedding_and_top_k(mock_index):
    provider = UpstashVectorQueryProvider(url="url", token="token")

    provider.query(embedding=[0.1, 0.2, 0.3], top_k=5)

    mock_index.return_value.query.assert_called_once_with(
        vector=[0.1, 0.2, 0.3],
        top_k=5,
        include_metadata=True,
    )


@patch("aegis.retrieval.providers.upstash.Index")
def test_query_translates_sdk_results_into_vector_matches(mock_index):
    sdk_result = MagicMock(id="1A00", score=0.91, metadata={"code": "1A00", "title": "Cholera"})
    mock_index.return_value.query.return_value = [sdk_result]

    provider = UpstashVectorQueryProvider(url="url", token="token")

    matches = provider.query(embedding=[0.1, 0.2, 0.3], top_k=5)

    assert len(matches) == 1
    assert matches[0].id == "1A00"
    assert matches[0].score == 0.91
    assert matches[0].metadata == {"code": "1A00", "title": "Cholera"}


@patch("aegis.retrieval.providers.upstash.Index")
def test_query_defaults_missing_metadata_to_empty_dict(mock_index):
    sdk_result = MagicMock(id="1A00", score=0.91, metadata=None)
    mock_index.return_value.query.return_value = [sdk_result]

    provider = UpstashVectorQueryProvider(url="url", token="token")

    matches = provider.query(embedding=[0.1, 0.2, 0.3], top_k=5)

    assert matches[0].metadata == {}
