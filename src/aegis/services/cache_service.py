"""
CacheService

Implements application_service_contracts/cache_service.md.

Establishes the deterministic clinical-knowledge-reuse boundary of
AEGIS: given a ``NormalizedClinicalNote``, determine whether a
physician-approved ``ClinicalDecision`` already exists for a
semantically identical observation.

This is not a performance cache. It never contains AI output,
confidence scores, retrieval candidates, embeddings, or prompt context
— only physician-approved ``ClinicalDecision`` artifacts, keyed by a
deterministic hash of a cache-specific canonical representation.

This module intentionally has no dependency on Redis, KeyDB, SQLite,
Upstash Vector, embeddings, vector search, LLM providers, CrewAI, or
LangGraph. Storage is expressed only through the
``ClinicalDecisionCacheRepository`` protocol; concrete adapters are
injected by the caller.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from abc import ABC, abstractmethod
from typing import Protocol

from aegis.models.clinical_decision import ClinicalDecision
from aegis.models.normalized_clinical_note import NormalizedClinicalNote

CACHE_KEY_VERSION = "1.0"


class ClinicalDecisionCacheRepository(Protocol):
    """
    Persistence boundary for cached, physician-approved
    ``ClinicalDecision`` lookups.

    ``CacheService`` depends on this abstraction rather than on any
    cache technology (Redis, KeyDB, Memcached, ...), so the underlying
    storage mechanism can change without affecting application
    behavior.
    """

    def get(self, cache_key: str) -> ClinicalDecision | None: ...

    def set(self, cache_key: str, decision: ClinicalDecision) -> None: ...


class CacheCanonicalizationRuleSet(Protocol):
    """
    Aggressive text canonicalization used only to derive cache identity.

    Distinct from ``NormalizationRuleSet``
    (``aegis.services.normalization_service``), which must never change
    clinical meaning. This rule set exists purely to maximize the rate
    at which semantically identical observations converge on the same
    cache key (e.g. case, punctuation, and whitespace differences), and
    its output is never used as clinical evidence or shown to a
    physician or reasoning component.
    """

    version: str

    def canonicalize(self, text: str) -> str: ...


class CacheKeyGenerator(Protocol):
    """Derives the deterministic cache identity for a ``NormalizedClinicalNote``."""

    def generate(self, normalized_note: NormalizedClinicalNote) -> str: ...


class AggressiveCacheCanonicalizationRuleSet:
    """
    Default ``CacheCanonicalizationRuleSet``.

    Applies, in order:

    1. Unicode normalization (NFKC) and case folding
    2. Punctuation removal
    3. Whitespace collapse

    This deliberately discards distinctions that
    ``DeterministicNormalizationRuleSet`` preserves — cache identity
    only needs to recognize "the same observation", not preserve
    clinical wording.
    """

    version = CACHE_KEY_VERSION

    _PUNCTUATION_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
    _WHITESPACE_RE = re.compile(r"\s+")

    def canonicalize(self, text: str) -> str:
        folded = unicodedata.normalize("NFKC", text).casefold()
        without_punctuation = self._PUNCTUATION_RE.sub("", folded)
        return self._WHITESPACE_RE.sub(" ", without_punctuation).strip()


class SHA256CacheKeyGenerator:
    """
    Default ``CacheKeyGenerator``.

    Canonicalizes ``normalized_note.normalized_text`` via a
    ``CacheCanonicalizationRuleSet``, then hashes the canonical
    representation with SHA-256, per the "Canonical Identity
    Generation" flow in application_service_contracts/cache_service.md.

    The rule-set version and the note's own
    ``normalization_version`` are folded into the digest input alongside
    the canonical text, so that a change to either normalization
    specification produces a distinct cache key rather than silently
    reusing decisions approved under a different specification.
    """

    def __init__(self, rule_set: CacheCanonicalizationRuleSet | None = None) -> None:
        self._rule_set = rule_set or AggressiveCacheCanonicalizationRuleSet()

    def generate(self, normalized_note: NormalizedClinicalNote) -> str:
        canonical_text = self._rule_set.canonicalize(normalized_note.normalized_text)
        digest_input = (
            f"{normalized_note.normalization_version}:{self._rule_set.version}:{canonical_text}"
        )
        return hashlib.sha256(digest_input.encode("utf-8")).hexdigest()


class CacheService(ABC):
    """
    Application service boundary that recognizes when a normalized
    clinical observation already has a physician-approved
    ``ClinicalDecision``.

    Performs no clinical reasoning, retrieval, or persistence — see
    application_service_contracts/cache_service.md for the full
    boundary. In particular, this service never decides *when* to call
    ``store``; that ordering belongs to workflow orchestration, which
    must only call it after a ``ClinicalDecision`` has been durably
    persisted.
    """

    @abstractmethod
    def lookup(self, normalized_note: NormalizedClinicalNote) -> ClinicalDecision | None:
        """Return the physician-approved ``ClinicalDecision`` for this observation, or ``None``."""
        raise NotImplementedError

    @abstractmethod
    def store(self, normalized_note: NormalizedClinicalNote, decision: ClinicalDecision) -> None:
        """Record ``decision`` as reusable clinical truth for this observation's cache identity."""
        raise NotImplementedError


class DefaultCacheService(CacheService):
    """
    Concrete ``CacheService`` implementation.

    Dependencies are injected so the service remains deterministic and
    independently testable: given the same ``NormalizedClinicalNote``,
    key generator, and repository contents, it always produces the same
    lookup result.
    """

    def __init__(
        self,
        repository: ClinicalDecisionCacheRepository,
        key_generator: CacheKeyGenerator | None = None,
    ) -> None:
        self._repository = repository
        self._key_generator = key_generator or SHA256CacheKeyGenerator()

    def lookup(self, normalized_note: NormalizedClinicalNote) -> ClinicalDecision | None:
        cache_key = self._key_generator.generate(normalized_note)
        return self._repository.get(cache_key)

    def store(self, normalized_note: NormalizedClinicalNote, decision: ClinicalDecision) -> None:
        cache_key = self._key_generator.generate(normalized_note)
        self._repository.set(cache_key, decision)
