> ⚠️ **ARCHIVED — DUPLICATE.** This document restates the application service layer that is
> authoritatively defined in `application_service_finalized.md` and
> `application_service_contracts/` (higher precedence per `CLAUDE.md`). To keep one
> authoritative home per concept it has been moved here; the content is accurate but no
> longer maintained. See those sources and `docs/architecture.md` for current truth.

# AEGIS Clinical — Application Service Layer Architecture

## Overview

The Application Service Layer represents the executable business capability boundary of AEGIS.

While Runtime Domain Contracts define the stable language and artifacts flowing through the system, Application Services define:

- who creates those artifacts,
- who transforms them,
- who owns specific business capabilities,
- and where responsibility boundaries exist.

Application Services intentionally separate business operations from:

- LangGraph orchestration.
- Infrastructure technologies.
- AI frameworks.
- Persistence mechanisms.

The architectural principle is:

> LangGraph coordinates business capabilities. Application Services execute them.

The resulting architecture is:

```
FastAPI

    ↓

LangGraph Workflow

    ↓

Application Services

    ↓

Repositories / Infrastructure / AI Systems
```

---

# Design Philosophy

AEGIS follows a strict responsibility separation:

```
Clinical Observation

        ↓

Deterministic Processing

        ↓

Semantic Evidence Retrieval

        ↓

AI-Assisted Recommendation

        ↓

Physician Validation

        ↓

Institutional Clinical Truth

        ↓

Durable Persistence
```

Each application service owns exactly one transition.

No service should:

- duplicate another service's responsibility.
- contain workflow orchestration.
- directly manipulate unrelated infrastructure.
- bypass domain contracts.

---

# Application Service Contracts

The AEGIS runtime consists of eight primary application services.

---

# 1. ClinicalNoteService

## Purpose

`ClinicalNoteService` owns the creation of the initial immutable clinical observation artifact.

It represents the application boundary where physician-submitted clinical information enters the system.

The service creates:

```
ClinicalNote
```

which becomes the stable identity reference for the entire downstream pipeline.

---

## Responsibilities

ClinicalNoteService handles:

- clinical note identity creation.
- lifecycle initialization.
- source artifact registration.
- persistence of the initial clinical note reference.

---

## Does Not Handle

ClinicalNoteService does not:

- normalize content.
- remove PHI.
- perform AI processing.
- generate medical interpretations.

It only establishes the original clinical observation.

---

# 2. NormalizationService

## Purpose

`NormalizationService` owns deterministic preprocessing of clinical observations.

Its responsibility is transforming a source clinical note into a safe, reproducible representation suitable for downstream retrieval and reasoning.

It creates:

```
NormalizedClinicalNote
```

---

## Responsibilities

NormalizationService handles:

- PHI anonymization.
- deterministic text normalization.
- normalization version tracking.
- traceability to the original clinical note.

---

## Architectural Principle

Normalization must remain deterministic.

Given:

```
Same ClinicalNote

+

Same Normalization Version
```

the output should remain identical.

LLM-based interpretation is intentionally excluded from this stage.

---

# 3. CacheService

## Purpose

`CacheService` manages reuse of previously validated clinical knowledge.

The purpose of the cache is not merely performance optimization.

Its deeper purpose is:

> Reusing previously physician-approved clinical truth.

The cache becomes stronger as more physician-reviewed cases accumulate.

---

## Responsibilities

CacheService handles:

- normalized artifact lookup.
- deterministic cache key generation.
- retrieving previously approved ICD classifications.
- storing validated clinical decisions.

---

## Architectural Principle

CacheService only works with:

```
Physician-approved truth
```

It never stores:

- AI guesses.
- unvalidated recommendations.
- retrieval candidates.

---

# 4. RetrievalService

## Purpose

`RetrievalService` provides semantic lookup of relevant ICD-11 concepts.

Its responsibility is answering:

> "Which clinical concepts are semantically close to this normalized observation?"

It creates:

```
RetrievalResult
```

---

## Responsibilities

RetrievalService handles:

- embedding generation.
- vector search execution.
- translating provider responses into domain contracts.

---

## Does Not Handle

RetrievalService does not:

- diagnose.
- rank clinical correctness.
- select ICD codes.
- perform reasoning.

It provides evidence only.

---

## Architectural Principle

Semantic similarity is not clinical confidence.

Retrieval provides candidates.

It does not provide answers.

---

# 5. ContextAssembler

## Purpose

`ContextAssembler` prepares bounded, deterministic reasoning context for downstream intelligence systems.

It creates:

```
ReasoningContext
```

---

## Responsibilities

ContextAssembler handles:

- selecting useful candidates.
- ordering evidence.
- removing unnecessary information.
- controlling context size.
- preparing structured reasoning input.

---

## Architectural Principle

Context quality directly influences reasoning quality.

The ContextAssembler protects the reasoning layer by ensuring the LLM receives:

- relevant information.
- minimal information.
- explainable information.

---

## Does Not Handle

ContextAssembler does not:

- call LLMs.
- contain prompts.
- perform reasoning.
- make medical decisions.

---

# 6. ClinicalReasoningService

## Purpose

`ClinicalReasoningService` owns bounded clinical reasoning.

Its responsibility is:

> Given a bounded clinical evidence context, produce a structured clinical recommendation.

It creates:

```
CodingRecommendation
```

---

## Responsibilities

ClinicalReasoningService handles:

- invoking reasoning systems.
- coordinating CrewAI workflows.
- validating LLM outputs.
- producing structured recommendations.

---

## Internal Architecture

Conceptually:

```
ReasoningContext

        ↓

CrewAI

        ↓

LLM

        ↓

Pydantic Validation

        ↓

CodingRecommendation
```

---

## Does Not Handle

ClinicalReasoningService does not:

- persist decisions.
- update caches.
- determine workflow transitions.
- create clinical truth.

AI remains advisory.

---

# 7. ClinicalDecisionService

## Purpose

`ClinicalDecisionService` represents the authority boundary where physician review becomes institutional clinical truth.

It creates:

```
ClinicalDecision
```

---

## Responsibilities

ClinicalDecisionService handles:

- constructing final clinical decisions.
- comparing physician decisions against AI recommendations.
- classifying recommendation outcomes.
- preserving evaluation metadata.

---

## Architectural Principle

AI recommends.

Physicians decide.

The service guarantees that only physician-approved information becomes authoritative.

---

## Does Not Handle

ClinicalDecisionService does not:

- persist data.
- update Redis.
- call AI systems.
- manage workflow.

It only constructs the truth artifact.

---

# 8. PersistenceService

## Purpose

`PersistenceService` materializes authoritative clinical truth into durable and derived storage representations.

Its responsibility is:

> Preserve institutional clinical knowledge across required storage systems.

---

## Responsibilities

PersistenceService handles:

- durable persistence.
- repository coordination.
- transaction management.
- audit storage.
- derived cache projections.

---

## Architectural Principle

The system of record remains authoritative.

Derived projections such as Redis must never become the source of truth.

The relationship is:

```
ClinicalDecision

        ↓

PersistenceService

        ↓

Durable Storage

        ↓

Derived Projections
```

---

# Complete Runtime Flow

The complete AEGIS service interaction becomes:

```
ClinicalNote

    ↓

ClinicalNoteService

    ↓

NormalizationService

    ↓

NormalizedClinicalNote

    ↓

CacheService

    ↓

(Cache Miss)

    ↓

RetrievalService

    ↓

RetrievalResult

    ↓

ContextAssembler

    ↓

ReasoningContext

    ↓

ClinicalReasoningService

    ↓

CodingRecommendation

    ↓

Physician Review

    ↓

ClinicalDecisionService

    ↓

ClinicalDecision

    ↓

PersistenceService

    ↓

Institutional Knowledge
```

---

# LangGraph Relationship

LangGraph does not implement these capabilities.

It only coordinates them.

A LangGraph node should resemble:

```
NormalizationNode

↓

NormalizationService.normalize()
```

not:

```
NormalizationNode

↓

PHI removal

↓

Text parsing

↓

Database access

↓

Embedding generation
```

The workflow layer remains thin because business responsibilities already exist elsewhere.

---

# Architectural Benefits

This service boundary design provides:

## Replaceability

Infrastructure can change without affecting business logic.

Examples:

- Upstash Vector → another vector database.
- Redis → another cache.
- CrewAI → another agent framework.
- SQLite → another database.

---

## Testability

Each business capability can be tested independently.

Examples:

- deterministic normalization tests.
- retrieval evaluation.
- reasoning validation.
- decision construction tests.
- persistence consistency tests.

---

## Auditability

Every important transition has a clear artifact:

```
ClinicalNote

↓

NormalizedClinicalNote

↓

RetrievalResult

↓

ReasoningContext

↓

CodingRecommendation

↓

ClinicalDecision
```

---

## Safety

AI remains bounded.

The system maintains the separation:

```
AI Recommendation

≠

Clinical Truth
```

Only physician-approved decisions become institutional knowledge.

---

# Summary

The Application Service Layer is the backbone of AEGIS runtime execution.

Each service owns one business capability:

| Service | Capability |
|---|---|
| ClinicalNoteService | Establish clinical observation |
| NormalizationService | Deterministic preprocessing |
| CacheService | Reuse validated knowledge |
| RetrievalService | Retrieve semantic evidence |
| ContextAssembler | Prepare bounded reasoning context |
| ClinicalReasoningService | Generate AI recommendations |
| ClinicalDecisionService | Convert physician review into truth |
| PersistenceService | Preserve institutional knowledge |

Together, these services create a deterministic, auditable, and replaceable foundation where AI assists clinical workflows without becoming the source of clinical authority.