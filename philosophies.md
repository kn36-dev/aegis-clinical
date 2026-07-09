# AEGIS Clinical Coding System — Runtime Architecture Context (Post Offline Knowledge Compilation)

This document summarizes the current architectural state of AEGIS after completing the offline knowledge compilation subsystem. It captures the engineering philosophy, architectural boundaries, runtime responsibilities, and the agreed direction for the next phase of development.

---

# Project Objective

AEGIS is **not** primarily an ICD-11 coding assistant.

The clinical domain serves as a realistic case study for demonstrating production-grade AI systems engineering.

The repository exists to showcase engineering principles including:

- deterministic workflow orchestration
- bounded AI reasoning
- retrieval-first architecture
- evaluation-driven development
- provider abstraction
- dependency inversion
- explainability
- observability
- reproducibility
- production-quality software architecture

The intended audience is an AI Engineering hiring manager or Principal Engineer reviewing the repository within approximately ten minutes.

The desired conclusion is:

> "This engineer understands how production AI systems should actually be designed."

---

# Core Engineering Philosophy

The central philosophy governing the entire repository is:

> Deterministic systems own workflow execution.
> Probabilistic systems contribute bounded expertise.

Every architectural decision should reinforce this boundary.

The LLM never owns the application.

The application owns the LLM.

---

# Current System Decomposition

The architecture naturally separates into three major subsystems.

## Phase 1 — Offline Knowledge Compilation

Executed only when the ICD taxonomy changes.

```
WHO ICD-11 CSV
        │
        ├──────────────────────────────┐
        │                              │
        ▼                              ▼
SQLite Seeder              Representation Builder
        │                              │
        ▼                              ▼
Canonical SQLite        Embedding Provider
Taxonomy Database               │
                                ▼
                         Upstash Vector
```

Important characteristics:

- deterministic
- reproducible
- immutable outputs
- provider independent
- executed offline

The SQLite database and Upstash Vector are independent outputs of the same compilation process.

Neither depends upon the other.

---

## Phase 2 — Deterministic Runtime Preparation

No LLMs are involved.

Responsibilities include:

- anonymization
- normalization
- deterministic cache lookup
- semantic retrieval
- context assembly

Runtime flow:

```
Clinical Note
        │
        ▼
Anonymization
        │
        ▼
Normalization
        │
        ├───────────────┐
        │               │
        ▼               ▼
SHA-256 Hash      Embedding Provider
        │               │
        ▼               ▼
Redis Cache    Upstash Vector Retrieval
                        │
                        ▼
                Candidate Ranking
                        │
                        ▼
                Context Assembly
```

This phase remains entirely deterministic.

---

## Phase 3 — Bounded AI Reasoning

Only after deterministic preparation is complete does the system permit probabilistic reasoning.

```
ReasoningContext
        │
        ▼
CrewAI
        │
        ▼
PydanticAI Validation
        │
        ▼
Human Review
        │
        ▼
SQLite Persistence
```

CrewAI never directly interacts with:

- SQLite
- Redis
- Upstash Vector
- Embedding providers
- Representation builders

CrewAI only receives deterministic application context.

---

# Current Offline Compilation Status

Completed:

- SQLite taxonomy seeding
- immutable taxonomy models
- repository abstraction
- representation builder
- representation metadata contract
- embedding provider abstraction
- local embedding provider
- OpenAI embedding provider
- VectorDocument abstraction
- provider-independent VectorStore
- LocalVectorStore
- Upstash Vector adapter
- offline indexing pipeline
- resumable upload pipeline
- batch orchestration
- comprehensive indexing tests

The semantic compilation subsystem is considered complete.

---

# Runtime Retrieval Philosophy

Retrieval is intentionally limited in scope.

Its responsibility is only to retrieve semantically similar ICD concepts.

Retrieval does **not** perform diagnosis.

Retrieval does **not** interpret symptoms.

Retrieval does **not** make clinical decisions.

It only retrieves evidence.

---

# Two Consumers of Retrieval

The retrieval infrastructure supports two independent application services.

## Semantic Cache Lookup

Purpose:

Determine whether an incoming anonymized clinical note is semantically equivalent to a previously physician-approved case.

High similarity thresholds are combined with deterministic guardrails before cache reuse.

---

## Taxonomy Retrieval

Purpose:

Retrieve approximately 5–20 semantically related ICD concepts that become deterministic context for downstream AI reasoning.

CrewAI never performs retrieval itself.

---

# Context Assembly

Retrieval output should not be passed directly into CrewAI.

Instead:

```
RetrievalResult
        │
        ▼
Context Assembly
        │
        ▼
ReasoningContext
```

Context Assembly is responsible for:

- selecting candidates
- formatting taxonomy information
- ordering evidence
- attaching metadata
- constructing deterministic prompt context

---

# Stable Boundary Between Deterministic and Probabilistic Systems

The application should expose a single canonical object before any LLM interaction.

Conceptually:

```
ReasoningContext
```

Everything before this object is deterministic.

Everything after this object is probabilistic.

The LLM never accesses infrastructure directly.

---

# Storage Responsibilities

SQLite

- system of record
- mutable application state
- physician-approved decisions
- ICD taxonomy
- workflow persistence

Redis

- deterministic SHA-256 cache
- physician-approved decision cache
- exact-match optimization

Upstash Vector

- semantic nearest-neighbor index
- immutable embedded ICD representations
- retrieval infrastructure only

---

# Evaluation Philosophy

Functional correctness and AI quality remain separate concerns.

Traditional software tests verify:

- business logic
- repositories
- orchestration
- persistence
- deterministic behaviour

Evaluation suites measure:

- retrieval quality
- Recall@K
- MRR
- nDCG
- ICD recommendation quality
- regression over time

Evaluation exists to measure AI quality rather than software correctness.

---

# Current Architectural Direction

The next subsystem is not LangGraph.

The next subsystem is the runtime retrieval architecture.

The implementation order should be:

1. Canonical runtime domain contracts
2. Retrieval subsystem
3. Context Assembly
4. CrewAI reasoning layer
5. LangGraph orchestration
6. Evaluation expansion

LangGraph should orchestrate existing capabilities rather than define them.

---

# Most Important Architectural Principle

Every subsystem should reinforce one central message:

> The application governs the AI.

Deterministic software owns:

- workflow
- state
- retrieval
- caching
- validation
- persistence
- evaluation

Probabilistic AI contributes only bounded reasoning inside explicit architectural guardrails.

This principle is the defining narrative of the entire repository and should remain the lens through which future architectural decisions are evaluated.