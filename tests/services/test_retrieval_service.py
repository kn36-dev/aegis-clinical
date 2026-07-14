from datetime import datetime, timezone
from uuid import uuid4

import pytest

from aegis.models.clinical_note import ClinicalNote
from aegis.models.normalized_clinical_note import NormalizedClinicalNote
from aegis.models.retrieval import RetrievalRequest
from aegis.retrieval.providers.base import VectorMatch
from aegis.services.retrieval_service import DefaultRetrievalService, RetrievalService


class FakeEmbeddingProvider:
    """In-memory stand-in for ``EmbeddingProvider``, used only in tests."""

    def __init__(self, vector: list[float] | None = None) -> None:
        self._vector = vector or [0.1, 0.2, 0.3]
        self.embed_query_calls: list[str] = []

    def embed_query(self, text: str) -> list[float]:
        self.embed_query_calls.append(text)
        return self._vector


class FakeVectorQueryProvider:
    """In-memory stand-in for ``VectorQueryProvider``, used only in tests."""

    def __init__(self, matches: list[VectorMatch] | None = None) -> None:
        self._matches = matches if matches is not None else []
        self.query_calls: list[tuple[list[float], int]] = []

    def query(self, embedding: list[float], top_k: int) -> list[VectorMatch]:
        self.query_calls.append((embedding, top_k))
        return self._matches[:top_k]


def make_clinical_note() -> ClinicalNote:
    return ClinicalNote(
        case_id=uuid4(),
        patient_id=uuid4(),
        content_reference="content-store://clinical-notes/abc123",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def make_normalized_note(
    normalized_text: str = "Patient reports no fever. Mild cough.",
    clinical_note: ClinicalNote | None = None,
) -> NormalizedClinicalNote:
    return NormalizedClinicalNote(
        clinical_note=clinical_note or make_clinical_note(),
        normalized_text=normalized_text,
        normalization_version="1.0",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def make_match(
    icd_code: str = "1A00",
    title: str = "Cholera",
    score: float = 0.91,
    context_path: str | None = "Chapter 1 → 1A00",
    chapter_number: str | None = "01",
    embedded_text: str = "Cholera is an acute diarrheal infection.",
) -> VectorMatch:
    return VectorMatch(
        id=icd_code,
        score=score,
        metadata={
            "code": icd_code,
            "title": title,
            "context_path": context_path,
            "chapter_number": chapter_number,
            "representation_type": "structured_prose",
            "embedded_text": embedded_text,
        },
    )


def make_request(
    top_k: int = 5,
    similarity_threshold: float | None = None,
    normalized_note: NormalizedClinicalNote | None = None,
) -> RetrievalRequest:
    note = normalized_note or make_normalized_note()
    return RetrievalRequest(
        clinical_note=note.clinical_note,
        normalized_note=note,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
    )


@pytest.fixture
def embedding_provider() -> FakeEmbeddingProvider:
    return FakeEmbeddingProvider()


@pytest.fixture
def query_provider() -> FakeVectorQueryProvider:
    return FakeVectorQueryProvider(matches=[make_match()])


@pytest.fixture
def service(
    embedding_provider: FakeEmbeddingProvider,
    query_provider: FakeVectorQueryProvider,
) -> DefaultRetrievalService:
    return DefaultRetrievalService(
        embedding_provider=embedding_provider,
        query_provider=query_provider,
    )


class TestRetrievalServiceInterface:
    def test_interface_cannot_be_instantiated_directly(self):
        with pytest.raises(TypeError):
            RetrievalService()  # type: ignore[abstract]

    def test_default_implementation_satisfies_interface(self, service: DefaultRetrievalService):
        assert isinstance(service, RetrievalService)


class TestEmbeddingGeneration:
    def test_retrieve_embeds_the_normalized_query_text(
        self,
        service: DefaultRetrievalService,
        embedding_provider: FakeEmbeddingProvider,
    ):
        request = make_request()

        service.retrieve(request)

        assert embedding_provider.embed_query_calls == [request.normalized_note.normalized_text]


class TestVectorLookup:
    def test_retrieve_queries_using_generated_embedding_and_top_k(
        self,
        service: DefaultRetrievalService,
        embedding_provider: FakeEmbeddingProvider,
        query_provider: FakeVectorQueryProvider,
    ):
        request = make_request(top_k=7)

        service.retrieve(request)

        [(embedding, top_k)] = query_provider.query_calls
        assert embedding == embedding_provider._vector
        assert top_k == 7


class TestResultTranslation:
    def test_translates_vector_matches_into_retrieval_candidates(
        self, service: DefaultRetrievalService
    ):
        result = service.retrieve(make_request())

        assert len(result.candidates) == 1
        candidate = result.candidates[0]
        assert candidate.icd_code == "1A00"
        assert candidate.title == "Cholera"
        assert candidate.hierarchy_context == "Chapter 1 → 1A00"
        assert candidate.chapter_number == "01"
        assert candidate.semantic_representation == "Cholera is an acute diarrheal infection."
        assert candidate.similarity_score == 0.91

    def test_caller_does_not_need_provider_specific_knowledge(
        self, service: DefaultRetrievalService
    ):
        # The result is composed entirely of canonical domain objects —
        # no Upstash/vector-provider types leak through.
        from aegis.models.retrieval import RetrievalCandidate, RetrievalResult

        result = service.retrieve(make_request())

        assert isinstance(result, RetrievalResult)
        assert all(isinstance(c, RetrievalCandidate) for c in result.candidates)

    def test_result_references_the_originating_normalized_note(
        self, service: DefaultRetrievalService
    ):
        request = make_request()

        result = service.retrieve(request)

        assert result.normalized_note == request.normalized_note


class TestCandidateBounds:
    def test_result_respects_top_k(self, embedding_provider: FakeEmbeddingProvider):
        matches = [make_match(icd_code=f"1A0{i}") for i in range(10)]
        query_provider = FakeVectorQueryProvider(matches=matches)
        service = DefaultRetrievalService(
            embedding_provider=embedding_provider, query_provider=query_provider
        )

        result = service.retrieve(make_request(top_k=3))

        assert len(result.candidates) == 3

    def test_similarity_threshold_filters_out_lower_scoring_candidates(
        self, embedding_provider: FakeEmbeddingProvider
    ):
        matches = [
            make_match(icd_code="1A00", score=0.95),
            make_match(icd_code="1A01", score=0.40),
        ]
        query_provider = FakeVectorQueryProvider(matches=matches)
        service = DefaultRetrievalService(
            embedding_provider=embedding_provider, query_provider=query_provider
        )

        result = service.retrieve(make_request(top_k=5, similarity_threshold=0.5))

        assert [c.icd_code for c in result.candidates] == ["1A00"]


class TestDeterministicBehavior:
    def test_same_request_and_provider_outputs_produce_same_result(
        self, embedding_provider: FakeEmbeddingProvider
    ):
        query_provider = FakeVectorQueryProvider(matches=[make_match()])
        service = DefaultRetrievalService(
            embedding_provider=embedding_provider, query_provider=query_provider
        )
        request = make_request()

        first = service.retrieve(request)
        second = service.retrieve(request)

        assert first == second


class TestRetrievalServiceDoesNotRankOrReason:
    def test_service_exposes_only_retrieve(self):
        public_methods = {name for name in vars(RetrievalService) if not name.startswith("_")}

        assert public_methods == {"retrieve"}
