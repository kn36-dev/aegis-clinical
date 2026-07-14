from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegis.models.clinical_note import ClinicalNote
from aegis.models.normalized_clinical_note import NormalizedClinicalNote
from aegis.phi.base import PHIAnonymizer
from aegis.services.normalization_service import (
    DefaultNormalizationService,
    DeterministicNormalizationRuleSet,
    NormalizationService,
)


class FakeClinicalNoteContentRepository:
    """In-memory stand-in for ``ClinicalNoteContentRepository``."""

    def __init__(self, content_by_reference: dict[str, str]) -> None:
        self._content_by_reference = content_by_reference
        self.requested_references: list[str] = []

    def get_content(self, content_reference: str) -> str:
        self.requested_references.append(content_reference)
        return self._content_by_reference[content_reference]


class FakePHIAnonymizer(PHIAnonymizer):
    """
    Records the text it was asked to anonymize and returns a fixed,
    deterministic anonymized string — used to verify pipeline ordering
    and interaction without depending on Presidio.
    """

    def __init__(self, anonymized_text: str = "[ANONYMIZED]") -> None:
        self._anonymized_text = anonymized_text
        self.received_text: list[str] = []

    def anonymize(self, text: str) -> str:
        self.received_text.append(text)
        return self._anonymized_text


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self._value = value

    def now(self) -> datetime:
        return self._value


@pytest.fixture
def clinical_note() -> ClinicalNote:
    return ClinicalNote(
        case_id=uuid4(),
        patient_id=uuid4(),
        content_reference="content-store://clinical-notes/abc123",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def content_repository() -> FakeClinicalNoteContentRepository:
    return FakeClinicalNoteContentRepository(
        {"content-store://clinical-notes/abc123": "Patient reports no fever.  \n\tMild cough."}
    )


@pytest.fixture
def phi_anonymizer() -> FakePHIAnonymizer:
    return FakePHIAnonymizer()


@pytest.fixture
def fixed_created_at() -> datetime:
    return datetime(2026, 1, 2, tzinfo=timezone.utc)


@pytest.fixture
def service(
    content_repository: FakeClinicalNoteContentRepository,
    phi_anonymizer: FakePHIAnonymizer,
    fixed_created_at: datetime,
) -> DefaultNormalizationService:
    return DefaultNormalizationService(
        content_repository=content_repository,
        phi_anonymizer=phi_anonymizer,
        clock=FixedClock(fixed_created_at),
    )


class TestNormalizationServiceInterface:
    def test_interface_cannot_be_instantiated_directly(self):
        with pytest.raises(TypeError):
            NormalizationService()  # type: ignore[abstract]

    def test_default_implementation_satisfies_interface(self, service: DefaultNormalizationService):
        assert isinstance(service, NormalizationService)


class TestNormalizationPipeline:
    def test_retrieves_content_via_repository_using_content_reference(
        self,
        service: DefaultNormalizationService,
        content_repository: FakeClinicalNoteContentRepository,
        clinical_note: ClinicalNote,
    ):
        service.normalize(clinical_note)

        assert content_repository.requested_references == [clinical_note.content_reference]

    def test_applies_rule_set_before_phi_anonymization(
        self,
        service: DefaultNormalizationService,
        phi_anonymizer: FakePHIAnonymizer,
        clinical_note: ClinicalNote,
    ):
        service.normalize(clinical_note)

        # The raw content has irregular whitespace; the anonymizer must
        # receive the already-cleaned text, not the raw retrieved text.
        assert phi_anonymizer.received_text == ["Patient reports no fever. Mild cough."]

    def test_normalized_text_is_the_anonymizer_output(
        self,
        service: DefaultNormalizationService,
        clinical_note: ClinicalNote,
    ):
        normalized = service.normalize(clinical_note)

        assert normalized.normalized_text == "[ANONYMIZED]"

    def test_normalization_never_invokes_anonymizer_with_raw_unclean_text(
        self,
        content_repository: FakeClinicalNoteContentRepository,
        phi_anonymizer: FakePHIAnonymizer,
        clinical_note: ClinicalNote,
    ):
        service = DefaultNormalizationService(
            content_repository=content_repository, phi_anonymizer=phi_anonymizer
        )
        service.normalize(clinical_note)

        assert "\n" not in phi_anonymizer.received_text[0]
        assert "\t" not in phi_anonymizer.received_text[0]


class TestNormalizedClinicalNoteConstruction:
    def test_result_is_normalized_clinical_note(
        self, service: DefaultNormalizationService, clinical_note: ClinicalNote
    ):
        normalized = service.normalize(clinical_note)

        assert isinstance(normalized, NormalizedClinicalNote)

    def test_preserves_traceability_to_source_clinical_note(
        self, service: DefaultNormalizationService, clinical_note: ClinicalNote
    ):
        normalized = service.normalize(clinical_note)

        assert normalized.clinical_note == clinical_note

    def test_assigns_normalization_version_from_rule_set(
        self, service: DefaultNormalizationService, clinical_note: ClinicalNote
    ):
        normalized = service.normalize(clinical_note)

        assert normalized.normalization_version == DeterministicNormalizationRuleSet.version

    def test_assigns_creation_timestamp_via_clock(
        self,
        service: DefaultNormalizationService,
        clinical_note: ClinicalNote,
        fixed_created_at: datetime,
    ):
        normalized = service.normalize(clinical_note)

        assert normalized.created_at == fixed_created_at

    def test_result_is_immutable(
        self, service: DefaultNormalizationService, clinical_note: ClinicalNote
    ):
        normalized = service.normalize(clinical_note)

        with pytest.raises(ValidationError):
            normalized.normalized_text = "mutated"


class TestNormalizationDeterminism:
    def test_same_inputs_produce_identical_output(
        self,
        content_repository: FakeClinicalNoteContentRepository,
        clinical_note: ClinicalNote,
        fixed_created_at: datetime,
    ):
        first_service = DefaultNormalizationService(
            content_repository=content_repository,
            phi_anonymizer=FakePHIAnonymizer(),
            clock=FixedClock(fixed_created_at),
        )
        second_service = DefaultNormalizationService(
            content_repository=content_repository,
            phi_anonymizer=FakePHIAnonymizer(),
            clock=FixedClock(fixed_created_at),
        )

        first_result = first_service.normalize(clinical_note)
        second_result = second_service.normalize(clinical_note)

        assert first_result == second_result

    def test_changing_rule_set_version_changes_normalization_version(
        self,
        content_repository: FakeClinicalNoteContentRepository,
        phi_anonymizer: FakePHIAnonymizer,
        clinical_note: ClinicalNote,
    ):
        class RuleSetV2:
            version = "2.0"

            def apply(self, text: str) -> str:
                return " ".join(text.split())

        service = DefaultNormalizationService(
            content_repository=content_repository,
            phi_anonymizer=phi_anonymizer,
            rule_set=RuleSetV2(),
        )

        normalized = service.normalize(clinical_note)

        assert normalized.normalization_version == "2.0"


class TestDeterministicNormalizationRuleSet:
    def test_collapses_whitespace(self):
        rule_set = DeterministicNormalizationRuleSet()

        assert rule_set.apply("Patient  reports\n\tno fever.") == "Patient reports no fever."

    def test_does_not_alter_clinical_meaning(self):
        rule_set = DeterministicNormalizationRuleSet()

        assert rule_set.apply("No fever.") == "No fever."

    def test_normalizes_unicode_to_nfc(self):
        rule_set = DeterministicNormalizationRuleSet()

        # "e" + combining acute accent (U+0065 U+0301) must normalize to
        # the single precomposed codepoint U+00E9.
        decomposed = "caf" + "\u0065\u0301"
        precomposed = "caf" + "\u00e9"

        assert rule_set.apply(decomposed) == precomposed

    def test_is_deterministic_across_calls(self):
        rule_set = DeterministicNormalizationRuleSet()
        text = "Patient  reports   mild pain."

        assert rule_set.apply(text) == rule_set.apply(text)
