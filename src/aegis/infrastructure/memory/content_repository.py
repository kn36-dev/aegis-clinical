"""
FakeContentRepository

Deterministic in-memory ``ClinicalNoteContentRepository`` adapter
(``aegis.services.normalization_service``).

Lives under ``src/aegis`` rather than ``tests/`` for the same reason as
``clinical_decision_cache_repository.py`` in this package: the demo
profile's composition root constructs it at application startup, and
real shipped source cannot depend on ``tests/`` being importable at
runtime. ``tests/application/fakes.py`` re-exports it from here rather
than defining it twice.

Resolves any ``content_reference`` from an in-memory mapping supplied
at construction time, with no dependency on ``case_id`` -- this is the
same workaround ``scripts/demo_e2e.py`` and
``tests/integration/test_clinical_pipeline.py`` already use for the
documented "Live-Credential Content Seeding Gap"
(``docs/tradeoffs_and_limitations.md``): the real ``SQLiteContentStore``
requires a ``patient_case`` row to exist before content can be
associated with a reference, but no caller knows ``case_id`` before
``ClinicalNoteService`` generates it during submission.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID


class FakeContentRepository:
    """In-memory stand-in for ``ClinicalNoteContentRepository``."""

    def __init__(self, content_by_reference: dict[str, str] | None = None) -> None:
        self._content = content_by_reference or {}

    def get_content(self, content_reference: str) -> str:
        return self._content.get(content_reference, "Patient reports no fever. Mild cough.")

    def save_content(self, case_id: UUID, content_reference: str, content_payload: str) -> None:
        """
        Seed content for ``content_reference``, ignoring ``case_id``.

        The in-memory mapping has no case-identity dependency (see this
        module's docstring), unlike ``SQLiteContentStore`` -- this exists so
        ``POST /clinical-notes/ingest`` works identically against the
        demo/integration profile's fake as it does against the real adapter.
        """
        self._content[content_reference] = content_payload
