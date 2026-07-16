from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from aegis.infrastructure.upstash.clinical_decision_cache_repository import (
    DEFAULT_TTL_SECONDS,
    UpstashClinicalDecisionCacheRepository,
)
from aegis.models.clinical_decision import (
    ApprovedICDClassification,
    ClinicalDecision,
    RecommendationDisposition,
)


def _make_decision() -> ClinicalDecision:
    return ClinicalDecision(
        decision_id=uuid4(),
        case_id=uuid4(),
        patient_id_reference=uuid4(),
        approved_icd_codes=[
            ApprovedICDClassification(
                icd_code="1A00", disposition=RecommendationDisposition.ACCEPTED
            ),
        ],
        normalization_version="1.0",
        created_at=datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc),
    )


@patch("aegis.infrastructure.upstash.clinical_decision_cache_repository.Redis")
def test_constructs_client_from_url_and_token(mock_redis_cls):
    UpstashClinicalDecisionCacheRepository(url="https://example.upstash.io", token="secret")

    mock_redis_cls.assert_called_once_with(url="https://example.upstash.io", token="secret")


@patch("aegis.infrastructure.upstash.clinical_decision_cache_repository.Redis")
def test_get_returns_none_on_cache_miss(mock_redis_cls):
    mock_client = MagicMock()
    mock_redis_cls.return_value = mock_client
    mock_client.get.return_value = None
    repository = UpstashClinicalDecisionCacheRepository(url="url", token="token")

    assert repository.get("cache-key") is None


@patch("aegis.infrastructure.upstash.clinical_decision_cache_repository.Redis")
def test_get_deserializes_stored_json_into_clinical_decision(mock_redis_cls):
    mock_client = MagicMock()
    mock_redis_cls.return_value = mock_client
    decision = _make_decision()
    mock_client.get.return_value = decision.model_dump_json()
    repository = UpstashClinicalDecisionCacheRepository(url="url", token="token")

    retrieved = repository.get("cache-key")

    assert retrieved == decision


@patch("aegis.infrastructure.upstash.clinical_decision_cache_repository.Redis")
def test_get_uses_namespaced_key(mock_redis_cls):
    mock_client = MagicMock()
    mock_redis_cls.return_value = mock_client
    mock_client.get.return_value = None
    repository = UpstashClinicalDecisionCacheRepository(url="url", token="token")

    repository.get("cache-key")

    mock_client.get.assert_called_once_with("aegis:clinical-decision-cache:cache-key")


@patch("aegis.infrastructure.upstash.clinical_decision_cache_repository.Redis")
def test_set_serializes_decision_with_ttl_and_namespaced_key(mock_redis_cls):
    mock_client = MagicMock()
    mock_redis_cls.return_value = mock_client
    decision = _make_decision()
    repository = UpstashClinicalDecisionCacheRepository(url="url", token="token")

    repository.set("cache-key", decision)

    mock_client.set.assert_called_once_with(
        "aegis:clinical-decision-cache:cache-key",
        decision.model_dump_json(),
        ex=DEFAULT_TTL_SECONDS,
    )


@patch("aegis.infrastructure.upstash.clinical_decision_cache_repository.Redis")
def test_set_respects_custom_ttl(mock_redis_cls):
    mock_client = MagicMock()
    mock_redis_cls.return_value = mock_client
    decision = _make_decision()
    repository = UpstashClinicalDecisionCacheRepository(url="url", token="token", ttl_seconds=60)

    repository.set("cache-key", decision)

    mock_client.set.assert_called_once_with(
        "aegis:clinical-decision-cache:cache-key",
        decision.model_dump_json(),
        ex=60,
    )


@patch("aegis.infrastructure.upstash.clinical_decision_cache_repository.Redis")
def test_round_trip_through_a_fake_in_memory_store(mock_redis_cls):
    """Exercises `set` then `get` through a dict-backed fake, proving the pair is symmetric."""
    store: dict[str, str] = {}
    mock_client = MagicMock()
    mock_redis_cls.return_value = mock_client
    mock_client.set.side_effect = lambda key, value, ex=None: store.__setitem__(key, value)
    mock_client.get.side_effect = lambda key: store.get(key)
    repository = UpstashClinicalDecisionCacheRepository(url="url", token="token")
    decision = _make_decision()

    repository.set("cache-key", decision)
    retrieved = repository.get("cache-key")

    assert retrieved == decision
