from datetime import datetime, timezone
from uuid import uuid4

import pytest

from aegis.models.clinical_decision import (
    ApprovedICDClassification,
    ClinicalDecision,
    RecommendationDisposition,
)
from aegis.models.clinical_note import ClinicalNote
from aegis.models.normalized_clinical_note import NormalizedClinicalNote
from aegis.services.cache_service import (
    AggressiveCacheCanonicalizationRuleSet,
    CacheService,
    DefaultCacheService,
    SHA256CacheKeyGenerator,
)


class FakeClinicalDecisionCacheRepository:
    """In-memory stand-in for ``ClinicalDecisionCacheRepository``, used only in tests."""

    def __init__(self) -> None:
        self._decisions_by_key: dict[str, ClinicalDecision] = {}
        self.get_calls: list[str] = []
        self.set_calls: list[tuple[str, ClinicalDecision]] = []

    def get(self, cache_key: str) -> ClinicalDecision | None:
        self.get_calls.append(cache_key)
        return self._decisions_by_key.get(cache_key)

    def set(self, cache_key: str, decision: ClinicalDecision) -> None:
        self.set_calls.append((cache_key, decision))
        self._decisions_by_key[cache_key] = decision

    def seed(self, cache_key: str, decision: ClinicalDecision) -> None:
        self._decisions_by_key[cache_key] = decision


def make_clinical_note(text_seed: str = "abc123") -> ClinicalNote:
    return ClinicalNote(
        case_id=uuid4(),
        patient_id=uuid4(),
        content_reference=f"content-store://clinical-notes/{text_seed}",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def make_normalized_note(
    normalized_text: str,
    normalization_version: str = "1.0",
    clinical_note: ClinicalNote | None = None,
) -> NormalizedClinicalNote:
    return NormalizedClinicalNote(
        clinical_note=clinical_note or make_clinical_note(),
        normalized_text=normalized_text,
        normalization_version=normalization_version,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def make_decision(case_id=None, normalization_version: str = "1.0") -> ClinicalDecision:
    return ClinicalDecision(
        decision_id=uuid4(),
        case_id=case_id or uuid4(),
        patient_id_reference=uuid4(),
        approved_icd_codes=[
            ApprovedICDClassification(
                icd_code="1A00", disposition=RecommendationDisposition.ACCEPTED
            )
        ],
        normalization_version=normalization_version,
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )


@pytest.fixture
def repository() -> FakeClinicalDecisionCacheRepository:
    return FakeClinicalDecisionCacheRepository()


@pytest.fixture
def service(repository: FakeClinicalDecisionCacheRepository) -> DefaultCacheService:
    return DefaultCacheService(repository=repository)


@pytest.fixture
def normalized_note() -> NormalizedClinicalNote:
    return make_normalized_note("Patient reports no fever. Mild cough.")


@pytest.fixture
def decision() -> ClinicalDecision:
    return make_decision()


class TestCacheServiceInterface:
    def test_interface_cannot_be_instantiated_directly(self):
        with pytest.raises(TypeError):
            CacheService()  # type: ignore[abstract]

    def test_default_implementation_satisfies_interface(self, service: DefaultCacheService):
        assert isinstance(service, CacheService)


class TestCacheLookup:
    def test_miss_returns_none(
        self, service: DefaultCacheService, normalized_note: NormalizedClinicalNote
    ):
        assert service.lookup(normalized_note) is None

    def test_hit_returns_the_stored_clinical_decision(
        self,
        service: DefaultCacheService,
        repository: FakeClinicalDecisionCacheRepository,
        normalized_note: NormalizedClinicalNote,
        decision: ClinicalDecision,
    ):
        key_generator = SHA256CacheKeyGenerator()
        repository.seed(key_generator.generate(normalized_note), decision)

        result = service.lookup(normalized_note)

        assert result == decision

    def test_miss_does_not_raise_or_fabricate_a_decision(
        self, service: DefaultCacheService, normalized_note: NormalizedClinicalNote
    ):
        result = service.lookup(normalized_note)

        assert result is None

    def test_lookup_queries_repository_using_generated_cache_key(
        self,
        service: DefaultCacheService,
        repository: FakeClinicalDecisionCacheRepository,
        normalized_note: NormalizedClinicalNote,
    ):
        service.lookup(normalized_note)

        expected_key = SHA256CacheKeyGenerator().generate(normalized_note)
        assert repository.get_calls == [expected_key]


class TestCacheStore:
    def test_store_writes_through_repository_under_expected_key(
        self,
        service: DefaultCacheService,
        repository: FakeClinicalDecisionCacheRepository,
        normalized_note: NormalizedClinicalNote,
        decision: ClinicalDecision,
    ):
        service.store(normalized_note, decision)

        expected_key = SHA256CacheKeyGenerator().generate(normalized_note)
        assert repository.set_calls == [(expected_key, decision)]

    def test_stored_decision_is_retrievable_via_lookup(
        self,
        service: DefaultCacheService,
        normalized_note: NormalizedClinicalNote,
        decision: ClinicalDecision,
    ):
        service.store(normalized_note, decision)

        assert service.lookup(normalized_note) == decision

    def test_store_only_accepts_clinical_decision_objects(self):
        # Enforced structurally: store()'s signature only accepts
        # ClinicalDecision, which by contract cannot exist without
        # physician approval — there is no separate "provisional"
        # artifact type that could be passed here instead.
        from typing import get_type_hints

        hints = get_type_hints(DefaultCacheService.store)
        assert hints["decision"] is ClinicalDecision


class TestSHA256CacheKeyGeneratorDeterminism:
    def test_same_normalized_note_produces_identical_key(self):
        generator = SHA256CacheKeyGenerator()
        note = make_normalized_note("Patient reports no fever.")

        assert generator.generate(note) == generator.generate(note)

    def test_different_clinical_content_produces_different_key(self):
        generator = SHA256CacheKeyGenerator()

        first = make_normalized_note("Patient reports no fever.")
        second = make_normalized_note("Patient reports high fever.")

        assert generator.generate(first) != generator.generate(second)

    def test_case_differences_produce_the_same_key(self):
        generator = SHA256CacheKeyGenerator()

        lower = make_normalized_note("patient reports no fever.")
        upper = make_normalized_note("PATIENT REPORTS NO FEVER.")

        assert generator.generate(lower) == generator.generate(upper)

    def test_insignificant_formatting_differences_produce_the_same_key(self):
        generator = SHA256CacheKeyGenerator()

        tight = make_normalized_note("Patient reports no fever.")
        spaced = make_normalized_note("Patient   reports,  no  fever")

        assert generator.generate(tight) == generator.generate(spaced)

    def test_different_normalization_version_produces_different_key(self):
        generator = SHA256CacheKeyGenerator()

        v1 = make_normalized_note("Patient reports no fever.", normalization_version="1.0")
        v2 = make_normalized_note("Patient reports no fever.", normalization_version="2.0")

        assert generator.generate(v1) != generator.generate(v2)

    def test_key_is_a_sha256_hex_digest(self):
        generator = SHA256CacheKeyGenerator()
        note = make_normalized_note("Patient reports no fever.")

        key = generator.generate(note)

        assert len(key) == 64
        assert all(char in "0123456789abcdef" for char in key)

    def test_custom_rule_set_version_change_produces_different_key(self):
        class RuleSetV2:
            version = "2.0"

            def canonicalize(self, text: str) -> str:
                return AggressiveCacheCanonicalizationRuleSet().canonicalize(text)

        note = make_normalized_note("Patient reports no fever.")

        default_key = SHA256CacheKeyGenerator().generate(note)
        v2_key = SHA256CacheKeyGenerator(rule_set=RuleSetV2()).generate(note)

        assert default_key != v2_key


class TestAggressiveCacheCanonicalizationRuleSet:
    def test_lowercases_text(self):
        rule_set = AggressiveCacheCanonicalizationRuleSet()

        assert rule_set.canonicalize("PATIENT") == "patient"

    def test_strips_punctuation(self):
        rule_set = AggressiveCacheCanonicalizationRuleSet()

        assert rule_set.canonicalize("no fever, mild cough.") == "no fever mild cough"

    def test_collapses_whitespace(self):
        rule_set = AggressiveCacheCanonicalizationRuleSet()

        assert rule_set.canonicalize("no  fever\n\tmild cough") == "no fever mild cough"

    def test_is_deterministic_across_calls(self):
        rule_set = AggressiveCacheCanonicalizationRuleSet()
        text = "Patient reports no fever."

        assert rule_set.canonicalize(text) == rule_set.canonicalize(text)


class TestCacheServiceDoesNotPerformReasoning:
    def test_service_exposes_only_lookup_and_store(self):
        public_methods = {name for name in vars(CacheService) if not name.startswith("_")}

        assert public_methods == {"lookup", "store"}
