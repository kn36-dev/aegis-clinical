from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from aegis.models.clinical_note import ClinicalNote
from aegis.models.workflow_commands import ClinicalNoteSubmission
from aegis.services.clinical_note_service import (
    ClinicalNoteService,
    DefaultClinicalNoteService,
)


class FakeClinicalNoteRepository:
    """In-memory stand-in for ``ClinicalNoteRepository``, used only in tests."""

    def __init__(self) -> None:
        self.saved: list[ClinicalNote] = []

    def save(self, clinical_note: ClinicalNote) -> None:
        self.saved.append(clinical_note)


class FailingClinicalNoteRepository:
    """Repository stub that always fails to persist, for propagation tests."""

    def save(self, clinical_note: ClinicalNote) -> None:
        raise RuntimeError("storage unavailable")


class FixedIdentifierGenerator:
    def __init__(self, value: UUID) -> None:
        self._value = value

    def generate(self) -> UUID:
        return self._value


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self._value = value

    def now(self) -> datetime:
        return self._value


@pytest.fixture
def submission() -> ClinicalNoteSubmission:
    return ClinicalNoteSubmission(
        patient_id=uuid4(),
        content_reference="content-store://clinical-notes/abc123",
    )


@pytest.fixture
def repository() -> FakeClinicalNoteRepository:
    return FakeClinicalNoteRepository()


@pytest.fixture
def fixed_case_id() -> UUID:
    return uuid4()


@pytest.fixture
def fixed_created_at() -> datetime:
    return datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def service(
    repository: FakeClinicalNoteRepository,
    fixed_case_id: UUID,
    fixed_created_at: datetime,
) -> DefaultClinicalNoteService:
    return DefaultClinicalNoteService(
        repository=repository,
        identifier_generator=FixedIdentifierGenerator(fixed_case_id),
        clock=FixedClock(fixed_created_at),
    )


class TestClinicalNoteServiceInterface:
    def test_interface_cannot_be_instantiated_directly(self):
        with pytest.raises(TypeError):
            ClinicalNoteService()  # type: ignore[abstract]

    def test_default_implementation_satisfies_interface(self, service: DefaultClinicalNoteService):
        assert isinstance(service, ClinicalNoteService)


class TestClinicalNoteCreation:
    def test_creates_clinical_note_from_submission(
        self,
        service: DefaultClinicalNoteService,
        submission: ClinicalNoteSubmission,
    ):
        clinical_note = service.create_clinical_note(submission)

        assert isinstance(clinical_note, ClinicalNote)
        assert clinical_note.patient_id == submission.patient_id
        assert clinical_note.content_reference == submission.content_reference

    def test_assigns_identity_via_identifier_generator(
        self,
        service: DefaultClinicalNoteService,
        submission: ClinicalNoteSubmission,
        fixed_case_id: UUID,
    ):
        clinical_note = service.create_clinical_note(submission)

        assert clinical_note.case_id == fixed_case_id

    def test_assigns_creation_timestamp_via_clock(
        self,
        service: DefaultClinicalNoteService,
        submission: ClinicalNoteSubmission,
        fixed_created_at: datetime,
    ):
        clinical_note = service.create_clinical_note(submission)

        assert clinical_note.created_at == fixed_created_at

    def test_two_submissions_receive_distinct_identity(
        self,
        repository: FakeClinicalNoteRepository,
    ):
        service = DefaultClinicalNoteService(repository=repository)

        first = service.create_clinical_note(
            ClinicalNoteSubmission(patient_id=uuid4(), content_reference="content-store://a")
        )
        second = service.create_clinical_note(
            ClinicalNoteSubmission(patient_id=uuid4(), content_reference="content-store://b")
        )

        assert first.case_id != second.case_id

    def test_default_dependencies_produce_a_valid_note(
        self, repository: FakeClinicalNoteRepository
    ):
        service = DefaultClinicalNoteService(repository=repository)

        clinical_note = service.create_clinical_note(
            ClinicalNoteSubmission(patient_id=uuid4(), content_reference="content-store://abc")
        )

        assert isinstance(clinical_note.case_id, UUID)
        assert clinical_note.created_at.tzinfo is not None

    def test_caller_supplied_case_id_is_used_verbatim(
        self,
        service: DefaultClinicalNoteService,
        submission: ClinicalNoteSubmission,
        fixed_case_id: UUID,
    ):
        """
        A caller-supplied ``case_id`` (e.g. the HTTP ingress layer fixing
        a LangGraph checkpoint identity ahead of graph invocation) must
        be assigned verbatim, taking priority over the injected
        ``IdentifierGenerator`` -- this is what lets ``ClinicalNote.case_id``,
        the LangGraph ``thread_id``, and ``patient_case.thread_id`` all be
        the same value end to end.
        """
        override_case_id = uuid4()
        assert override_case_id != fixed_case_id

        clinical_note = service.create_clinical_note(submission, case_id=override_case_id)

        assert clinical_note.case_id == override_case_id

    def test_omitted_case_id_falls_back_to_identifier_generator(
        self,
        service: DefaultClinicalNoteService,
        submission: ClinicalNoteSubmission,
        fixed_case_id: UUID,
    ):
        clinical_note = service.create_clinical_note(submission, case_id=None)

        assert clinical_note.case_id == fixed_case_id


class TestClinicalNoteImmutableConstruction:
    def test_created_note_is_immutable(
        self,
        service: DefaultClinicalNoteService,
        submission: ClinicalNoteSubmission,
    ):
        clinical_note = service.create_clinical_note(submission)

        with pytest.raises(ValidationError):
            clinical_note.content_reference = "content-store://mutated"


class TestClinicalNotePersistenceCoordination:
    def test_persists_exactly_once_through_repository(
        self,
        service: DefaultClinicalNoteService,
        repository: FakeClinicalNoteRepository,
        submission: ClinicalNoteSubmission,
    ):
        service.create_clinical_note(submission)

        assert len(repository.saved) == 1

    def test_persisted_note_matches_returned_note(
        self,
        service: DefaultClinicalNoteService,
        repository: FakeClinicalNoteRepository,
        submission: ClinicalNoteSubmission,
    ):
        clinical_note = service.create_clinical_note(submission)

        assert repository.saved[0] == clinical_note

    def test_repository_failure_propagates_and_is_not_swallowed(
        self, submission: ClinicalNoteSubmission
    ):
        service = DefaultClinicalNoteService(repository=FailingClinicalNoteRepository())

        with pytest.raises(RuntimeError, match="storage unavailable"):
            service.create_clinical_note(submission)


class TestClinicalNoteSubmissionValidation:
    def test_rejects_missing_patient_id(self):
        with pytest.raises(ValidationError):
            ClinicalNoteSubmission.model_validate({"content_reference": "content-store://abc123"})

    def test_rejects_missing_content_reference(self):
        with pytest.raises(ValidationError):
            ClinicalNoteSubmission.model_validate({"patient_id": str(uuid4())})
