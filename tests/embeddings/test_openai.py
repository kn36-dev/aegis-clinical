from unittest.mock import MagicMock, patch

from aegis.embeddings.openai import OpenAIEmbeddingProvider


@patch("aegis.embeddings.openai.OpenAI")
def test_embed_query_calls_sdk_with_plain_text(mock_openai_cls):
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=[0.1, 0.2, 0.3])]
    )

    provider = OpenAIEmbeddingProvider(api_key="key")

    embedding = provider.embed_query("Patient reports no fever.")

    mock_client.embeddings.create.assert_called_once_with(
        model="text-embedding-3-small",
        input="Patient reports no fever.",
    )
    assert embedding == [0.1, 0.2, 0.3]
