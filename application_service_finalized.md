# AEGIS Clinical — Architecture Handoff Summary

## Current Project State

AEGIS Clinical has completed the foundational architecture design phase.

The system has now defined:

1. Business Domain Concepts
2. Runtime Domain Contracts
3. Application Service Contracts

The architecture is ready to move into implementation.

The next phase is no longer architecture discovery.

The next phase is:

> Implement the Application Services and compose them through LangGraph orchestration.

---

# Architectural Evolution

The project has progressed through three conceptual layers.

---

# Layer 1 — Domain Truth

Purpose:

Define the immutable business concepts of AEGIS.

Examples:

- ClinicalNote
- ClinicalDecision

These represent business meaning.

They are independent of:

- FastAPI
- LangGraph
- CrewAI
- SQLite
- Redis
- Vector databases

---

# Layer 2 — Runtime Contracts

Purpose:

Define the artifacts flowing through the runtime pipeline.

Completed runtime contracts:

```
ClinicalNote

↓

NormalizedClinicalNote

↓

RetrievalRequest

↓

RetrievalResult

↓

ReasoningContext

↓

CodingRecommendation

↓

ClinicalDecision
```

These contracts define:

- ownership
- lifecycle
- boundaries
- authority levels

---

# Layer 3 — Application Services

Purpose:

Define who creates and transforms runtime artifacts.

The core principle:

> LangGraph orchestrates services. Services execute business capabilities.

LangGraph should never contain:

- embedding logic
- database logic
- normalization logic
- AI reasoning logic
- persistence logic

---

# Final Application Service Architecture

The complete service layer contains eight services.

---

# 1. ClinicalNoteService

## Purpose

Creates the immutable entry point into AEGIS.

Creates:

```
ClinicalNote
```

Responsibilities:

- clinical note identity creation
- lifecycle initialization
- source registration

Does not:

- normalize
- reason
- interpret
- classify

---

# 2. NormalizationService

## Purpose

Deterministically transforms clinical observations into safe processing artifacts.

Creates:

```
NormalizedClinicalNote
```

Responsibilities:

- PHI anonymization
- deterministic normalization
- normalization version tracking
- traceability

Important decision:

LLM-based symptom extraction was intentionally removed.

Reason:

Early probabilistic extraction creates cascading downstream errors.

Normalization must remain deterministic.

---

# 3. CacheService

## Purpose

Reuse previously validated physician-approved knowledge.

The cache is not primarily a performance optimization.

The deeper purpose:

> Reuse institutional clinical truth.

Responsibilities:

- normalized artifact lookup
- deterministic cache key generation
- approved ICD retrieval
- approved decision storage

Important boundary:

Cache only stores:

```
Physician-approved truth
```

Never:

- AI guesses
- recommendations
- retrieval candidates

---

# 4. RetrievalService

## Purpose

Retrieve semantically relevant ICD-11 concepts.

Creates:

```
RetrievalResult
```

Answers:

> "Which concepts are close in semantic space?"

Responsibilities:

- embedding generation
- vector search
- translating provider results into domain contracts

Does not:

- diagnose
- rank clinical correctness
- select ICD codes
- reason

Important philosophy:

Similarity ≠ clinical confidence.

---

# 5. ContextAssembler

## Purpose

Prepare bounded reasoning context.

Creates:

```
ReasoningContext
```

Responsibilities:

- candidate selection
- evidence ordering
- context trimming
- deterministic preparation

Does not:

- call LLMs
- contain prompts
- reason
- make decisions

Important philosophy:

The quality of reasoning depends heavily on the quality of context preparation.

---

# 6. ClinicalReasoningService

## Purpose

Own bounded AI-assisted reasoning.

Creates:

```
CodingRecommendation
```

Business capability:

> Given bounded clinical evidence, produce structured clinical recommendations.

Internal flow:

```
ReasoningContext

↓

CrewAI

↓

LLM

↓

Pydantic validation

↓

CodingRecommendation
```

Important boundaries:

AI recommendation ≠ truth.

Does not:

- persist
- update cache
- decide workflow
- create ClinicalDecision

---

# 7. ClinicalDecisionService

## Purpose

The authority transition point.

Creates:

```
ClinicalDecision
```

Business capability:

> Given AI recommendations and physician review, construct authoritative clinical truth.

Responsibilities:

- construct final decision
- compare AI recommendations vs physician decisions
- classify outcomes

Examples:

- accepted recommendation
- modified recommendation
- rejected recommendation
- manually added ICD code

Important philosophy:

```
AI recommends.

Physician decides.

ClinicalDecision becomes truth.
```

Does not:

- persist
- update Redis
- call AI
- manage workflow

---

# 8. PersistenceService

## Purpose

Materialize authoritative clinical truth.

Consumes:

```
ClinicalDecision
```

Responsibilities:

- durable persistence
- repository coordination
- audit storage
- derived projection updates

Architecture:

```
ClinicalDecision

↓

PersistenceService

↓

SQLite/system of record

↓

Redis projection
```

Important decision:

Redis is not truth.

Redis is a derived projection.

If Redis fails:

```
SQLite truth remains committed.

Redis is reconciled later.
```

---

# Important Contract Revision

ClinicalDecision was revised.

Previous issue:

It incorrectly implied:

```
ClinicalDecision

↓

Triggers persistence
```

New model:

```
ClinicalDecision

↓

PersistenceService

↓

Storage
```

ClinicalDecision remains a pure business artifact.

---

# Added Traceability Decision

ClinicalDecision should contain:

```
normalized_note_id
```

or equivalent normalization artifact reference.

Reason:

PersistenceService may need to derive projections such as Redis cache keys.

But the domain should not contain infrastructure artifacts like:

```
redis_key
sha256_hash
```

The domain stores traceability.

Infrastructure derives implementation details.

---

# Final Authority Hierarchy

The final AEGIS authority model:

```
ClinicalNote

=
Original physician observation


↓

NormalizedClinicalNote

=
Deterministic preprocessing


↓

RetrievalResult

=
Semantic evidence


↓

ReasoningContext

=
Bounded evidence provided to AI


↓

CodingRecommendation

=
AI opinion


↓

ClinicalDecision

=
Physician-approved truth


↓

Persistence

=
Institutional knowledge
```

---

# Current Architecture Philosophy

AEGIS is not:

```
User note

↓

LLM

↓

ICD code
```

It is:

```
Observation

↓

Deterministic preparation

↓

Evidence retrieval

↓

Bounded reasoning

↓

Human validation

↓

Institutional learning
```

---

# Completed Documentation

Created:

```
docs/

├── runtime-domain-contracts/
│
├── application-services/
│
│   ├── clinical-note-service.md
│   ├── normalization-service.md
│   ├── cache-service.md
│   ├── retrieval-service.md
│   ├── context-assembler.md
│   ├── clinical-reasoning-service.md
│   ├── clinical-decision-service.md
│   └── persistence-service.md
│
└── application-service-layer-overview.md
```

---

# What Is Ready To Build Next

The architecture is ready for implementation.

Recommended next phase:

## Phase B — Application Service Implementation

Order:

---

## 1. Define service interfaces

Example:

```python
class NormalizationService:

    def normalize(
        self,
        note: ClinicalNote
    ) -> NormalizedClinicalNote:
        ...
```

No infrastructure yet.

Only contracts.

---

## 2. Implement repository boundaries

Examples:

```
ClinicalNoteRepository

ClinicalDecisionRepository

PatientExtractedCodeRepository

AuditRepository

ClinicalCacheRepository
```

---

## 3. Implement deterministic services first

Recommended order:

1. ClinicalNoteService
2. NormalizationService
3. RetrievalService
4. ContextAssembler
5. CacheService
6. ClinicalDecisionService
7. PersistenceService
8. ClinicalReasoningService

Reason:

The AI boundary should be integrated after the deterministic pipeline exists.

---

## 4. Create LangGraph skeleton

LangGraph should initially be thin:

```
START

↓

normalize_node

↓

cache_node

↓

retrieve_node

↓

assemble_context_node

↓

reason_node

↓

human_review_node

↓

decision_node

↓

persist_node

↓

END
```

Each node calls exactly one application service.

---

## 5. Integrate CrewAI

Only after:

```
ClinicalReasoningService
```

exists.

CrewAI becomes an internal implementation detail.

The service contract remains:

```
ReasoningContext

↓

CodingRecommendation
```

---

# Final Status

Architecture discovery:

✅ Complete

Runtime contracts:

✅ Complete

Application service contracts:

✅ Complete

Ready for:

🚀 Service implementation

🚀 LangGraph orchestration

🚀 CrewAI integration

🚀 End-to-end AEGIS runtime pipeline