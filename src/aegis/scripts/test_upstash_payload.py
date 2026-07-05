from unittest.mock import patch

from aegis.indexing.documents import (
    RepresentationDocument,
    RepresentationType,
    VectorDocument,
)
from aegis.vectorstores.upstash import UpstashVectorStore

doc = VectorDocument(
    representation=RepresentationDocument(
        concept_id="A00",
        representation_type=RepresentationType.STRUCTURED_PROSE,
        text="dummy text",
        metadata={"source": "test", "category": "icd11"},
    ),
    embedding=[0.1, 0.2, 0.3],
)

with patch("aegis.vectorstores.upstash.Index") as MockIndex:
    store = UpstashVectorStore("https://example.com", "token")

    store.index(doc)

    print("\n=== DEBUG OUTPUT ===")
    print("Mock calls:", MockIndex.mock_calls)

    upsert_call = MockIndex.return_value.upsert.call_args
    print("Upsert call args:", upsert_call)

    assert upsert_call is not None, "Upsert was never called"

    payload = upsert_call.kwargs.get("vectors") or upsert_call.args

    print("\nPayload:", payload)

    assert payload is not None
