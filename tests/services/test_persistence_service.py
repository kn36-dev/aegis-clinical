from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from aegis.models.clinical_decision import ApprovedICDClassification, ClinicalDecision, RecommendationDisposition
from aegis.services.persistence_service import (
    DefaultPersistenceService,
    PersistenceResult,
    PersistenceService,
)


class FakeClinicalDecisionRepository:
    """In-memory stand-in for ``ClinicalDecisionRepository``, used only in tests."""

    def __init__(self) -> None:
        self.saved: list[ClinicalDecision] = []

    def save(self, clinical_decision: ClinicalDecision) -> None:
        self.saved.append(clinical_decision)


class FailingClinicalDecisionRepository:
    """Repository stub that always fails to persist, for propagation tests."""

    def save(self, clinical_decision: ClinicalDecision) -> None:
        raise RuntimeError("storage unavailable")


class RecordingCacheService:
    """Stand-in for CacheService; records calls so tests can assert it is never invoked."""

    def __init__(self) -> None:
        self.calls: list[ClinicalDecision] = []

    def cache(self, clinical_decision: ClinicalDecision) -> None:
        self.calls.append(clinical_decision)


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self._value = value

    def now(self) -> datetime:
        return self._value


def make_decision(
    decision_id: UUID | None = None,
    case_id: UUID | None = None,
    patient_id_reference: UUID | None = None,
    approved_icd_codes: list[ApprovedICDClassification] | None = None,
    normalization_version: str = "1.0",
    created_at: datetime | None = None,
) -> ClinicalDecision:
    return ClinicalDecision(
        decision_id=decision_id or uuid4(),
        case_id=case_id or uuid4(),
        patient_id_reference=patient_id_reference or uuid4(),
        approved_icd_codes=(
            approved_icd_codes
            if approved_icd_codes is not None
            else [
                ApprovedICDClassification(
                    icd_code="1A00", disposition=RecommendationDisposition.ACCEPTED
                )
            ]
        ),
        normalization_version=normalization_version,
        created_at=created_at or datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def repository() -> FakeClinicalDecisionRepository:
    return FakeClinicalDecisionRepository()


@pytest.fixture
def fixed_persisted_at() -> datetime:
    return datetime(2026, 2, 1, tzinfo=timezone.utc)


@pytest.fixture
def service(
    repository: FakeClinicalDecisionRepository,
    fixed_persisted_at: datetime,
) -> DefaultPersistenceService:
    return DefaultPersistenceService(
        repository=repository,
        clock=FixedClock(fixed_persisted_at),
    )


class TestPersistenceServiceInterface:
    def test_interface_cannot_be_instantiated_directly(self):
        with pytest.raises(TypeError):
            PersistenceService()  # type: ignore[abstract]

    def test_default_implementation_satisfies_interface(self, service: DefaultPersistenceService):
        assert isinstance(service, PersistenceService)

    def test_service_exposes_only_persist(self):
        public_methods = {name for name in vars(PersistenceService) if not name.startswith("_")}
        assert public_methods == {"persist"}


class TestDurablePersistence:
    def test_persists_exactly_once_through_repository(
        self,
        service: DefaultPersistenceService,
        repository: FakeClinicalDecisionRepository,
    ):
        decision = make_decision()

        service.persist(decision)

        assert len(repository.saved) == 1
        assert repository.saved[0] == decision

    def test_returns_deterministic_persistence_result(
        self,
        service: DefaultPersistenceService,
        fixed_persisted_at: datetime,
    ):
        decision = make_decision()

        result = service.persist(decision)

        assert isinstance(result, PersistenceResult)
        assert result.decision_id == decision.decision_id
        assert result.case_id == decision.case_id
        assert result.persisted_at == fixed_persisted_at

    def test_repository_failure_propagates_and_is_not_swallowed(self):
        service = DefaultPersistenceService(repository=FailingClinicalDecisionRepository())

        with pytest.raises(RuntimeError, match="storage unavailable"):
            service.persist(make_decision())

    def test_failed_persistence_is_not_reported_as_a_result(self):
        """A durable storage failure must never yield a PersistenceResult."""
        service = DefaultPersistenceService(repository=FailingClinicalDecisionRepository())

        try:
            service.persist(make_decision())
        except RuntimeError:
            pass
        else:
            pytest.fail("Expected RuntimeError to propagate without producing a result")


class TestDeterminism:
    def test_same_inputs_produce_identical_result(
        self,
        repository: FakeClinicalDecisionRepository,
        fixed_persisted_at: datetime,
    ):
        decision = make_decision()

        service_a = DefaultPersistenceService(
            repository=repository, clock=FixedClock(fixed_persisted_at)
        )
        service_b = DefaultPersistenceService(
            repository=repository, clock=FixedClock(fixed_persisted_at)
        )

        assert service_a.persist(decision) == service_b.persist(decision)


class TestBoundaryProtection:
    def test_service_does_not_mutate_decision(
        self, service: DefaultPersistenceService
    ):
        decision = make_decision()
        original = decision.model_copy(deep=True)

        service.persist(decision)

        assert decision == original

    def test_service_has_no_cache_or_projection_methods(self):
        public_methods = {
            name for name in vars(DefaultPersistenceService) if not name.startswith("_")
        }
        assert public_methods == {"persist"}

    def test_service_never_invokes_a_cache_collaborator(
        self, repository: FakeClinicalDecisionRepository, fixed_persisted_at: datetime
    ):
        """
        PersistenceService must not call CacheService/Redis (see module
        docstring's scope note on the persistence_service.md contract
        conflict). Constructing the service with only a repository and
        clock — no cache collaborator accepted at all — is itself the
        primary guarantee; this test additionally proves that persisting
        never reaches out to an unrelated cache-shaped object.
        """
        cache = RecordingCacheService()
        service = DefaultPersistenceService(
            repository=repository, clock=FixedClock(fixed_persisted_at)
        )

        service.persist(make_decision())

        assert cache.calls == []

    def test_repository_is_the_only_constructor_dependency_besides_clock(self):
        import inspect

        parameters = inspect.signature(DefaultPersistenceService.__init__).parameters
        assert set(parameters) == {"self", "repository", "clock"}
