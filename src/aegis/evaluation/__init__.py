"""
AEGIS evaluation framework.

Orchestration/reporting layer only: composes existing application
services (``RetrievalService``, ``NormalizationService``,
``ContextAssembler``, ``ClinicalReasoningService``) to measure retrieval
and reasoning quality against ``evals/clinical_cases.jsonl``. Introduces
no new business, retrieval, or reasoning logic of its own -- see
``docs/testing_and_evaluations.md`` for the current scope and deferred
future work (Braintrust, LLM-as-judge).
"""

from __future__ import annotations
