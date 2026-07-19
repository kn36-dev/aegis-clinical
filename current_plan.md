# AEGIS Clinical — Implementation Roadmap (Architectural Edition)

## Objective

AEGIS is a reference implementation demonstrating production-grade AI systems engineering through deterministic workflow orchestration, bounded AI reasoning, semantic retrieval, structured validation, and Human-in-the-Loop (HITL) decision making.

The implementation order deliberately follows architectural dependencies rather than framework dependencies. Every phase establishes a stable abstraction before introducing technologies that depend upon it.

> **Status legend (v1, as built).** This roadmap is largely realized. Snapshot:
> - **Phases 0–5, 7–9: shipped.** Offline knowledge compilation, runtime domain
>   contracts, deterministic application services, persistence, prompts, the CrewAI
>   reasoning boundary, the end-to-end LangGraph workflow, and the FastAPI layer are all
>   wired and running.
> - **Phase 6 (PydanticAI): deferred → Future v2.** v1 uses plain Pydantic for structured
>   validation. PydanticAI is a declared dependency but **not integrated**; introducing it
>   for typed agent/tool boundaries is a future evaluation, not a CrewAI replacement.
> - **Phase 10 (Observability): partially shipped as v1 workflow visibility.** Workflow
>   state is exposed through the `GET /api/v1/workflows/{workflow_id}` endpoint and the
>   React workflow-stage timeline / review queue. **OpenTelemetry distributed tracing is
>   Future v2** — not wired up.
> - **Phase 11 (Evaluation): shipped as a custom deterministic framework**
>   (`src/aegis/evaluation/`, `aegis-eval`) — Recall@K, Hit Rate@K, MRR, and deterministic
>   reasoning scoring. **Braintrust and LLM-as-judge are Future v2.**
> - Real endpoint names differ from the sketches below: ingest is
>   `POST /api/v1/clinical-notes`; review is `GET`/`POST /api/v1/reviews/{thread_id}[/decision]`
>   (no separate `/approve`/`/reject`/`/amend`); plus `GET /api/v1/demo/patients` and a
>   `GET /health` readiness probe. See `src/aegis/api/routers/api_contract_plan.md`.
> - Clinical trial matching (Phase-independent, referenced throughout) is **Future v2** —
>   scaffolding exists but is not wired into the app.

-------------------------------------------------------------------------------
Phase 0 — Foundation & Infrastructure
-------------------------------------------------------------------------------

Goal:

Establish deterministic application infrastructure.

Complete:

✓ Typed application configuration
✓ Dependency injection
✓ SQLite checkpoint database
✓ Upstash Vector client
✓ Upstash Redis client
✓ FastAPI lifespan
✓ Logging
✓ Environment configuration

Remaining:

• Remove duplicated LLM dependency
• Consolidate chat model provider
• Verify dependency wiring

Deliverable:

A deterministic application shell capable of running without AI logic.

-------------------------------------------------------------------------------
Phase 1 — Offline Knowledge Compilation
-------------------------------------------------------------------------------

Goal:

Prepare the immutable medical knowledge used during runtime.

Pipeline:

WHO ICD Dataset

↓

SQLite Taxonomy

↓

RepresentationBuilder

↓

Embedding Provider

↓

Upstash Vector

Responsibilities:

• Seed ICD taxonomy
• Build semantic representations
• Generate embeddings
• Upload vectors
• Verify retrieval quality

Deliverable:

A complete read-only semantic retrieval index.

-------------------------------------------------------------------------------
Phase 2 — Runtime Domain Language
-------------------------------------------------------------------------------

Goal:

Define the canonical runtime contracts.

Business Domain

• ClinicalNote
• ClinicalDecision

Processing Contracts

• NormalizedClinicalNote
• RetrievalRequest
• RetrievalResult
• ReasoningContext
• CodingRecommendation

Workflow

• LangGraph State

Principles:

• Immutable
• Technology independent
• Framework independent
• Business-oriented

Deliverable:

The ubiquitous runtime language spoken by every subsystem.

-------------------------------------------------------------------------------
Phase 3 — Application Services
-------------------------------------------------------------------------------

Goal:

Implement deterministic business services that transform runtime contracts.

Examples:

ClinicalNote

↓

NormalizationService

↓

NormalizedClinicalNote

↓

RetrievalService

↓

RetrievalResult

↓

ContextAssembler

↓

ReasoningContext

Each service owns exactly one responsibility.

No orchestration.

No AI.

No LangGraph.

Deliverable:

Composable deterministic application logic.

-------------------------------------------------------------------------------
Phase 4 — Persistence Layer
-------------------------------------------------------------------------------

Goal:

Implement repositories and storage abstractions.

SQLite

• Clinical repositories
• ICD repository
• Decision repository

Redis

• Deterministic cache

Vector

• Semantic retrieval

Repositories expose business operations rather than SQL.

Deliverable:

Technology-specific persistence hidden behind stable interfaces.

-------------------------------------------------------------------------------
Phase 5 — Prompt Layer
-------------------------------------------------------------------------------

Goal:

Define reusable reasoning instructions.

Prompts become versioned assets.

Examples:

Clinical reasoning

Evidence extraction

Ranking strategy

Prompt engineering remains completely isolated from execution.

Deliverable:

Version-controlled reasoning specifications.

-------------------------------------------------------------------------------
Phase 6 — PydanticAI Structured Inference
-------------------------------------------------------------------------------

Goal:

Define deterministic AI boundaries.

Responsibilities:

• Structured output schemas
• Validation
• Retry handling
• Output normalization

Every LLM interaction begins and ends with strongly typed contracts.

Deliverable:

Deterministic probabilistic boundaries.

-------------------------------------------------------------------------------
Phase 7 — CrewAI Reasoning Layer
-------------------------------------------------------------------------------

Goal:

Encapsulate domain reasoning.

Current design intentionally uses one specialist agent.

Responsibilities:

ReasoningContext

↓

Clinical Reasoning Agent

↓

CodingRecommendation

CrewAI owns reasoning only.

CrewAI never owns workflow.

Future specialist agents can be introduced without affecting orchestration.

Deliverable:

A stable reasoning boundary.

-------------------------------------------------------------------------------
Phase 8 — LangGraph Orchestration
-------------------------------------------------------------------------------

Goal:

Connect deterministic services into a resumable workflow.

Nodes transform one runtime contract into another.

Example:

ClinicalNote

↓

Normalize Node

↓

NormalizedClinicalNote

↓

Retrieval Node

↓

RetrievalResult

↓

Context Assembly

↓

ReasoningContext

↓

CrewAI Node

↓

CodingRecommendation

↓

Human Review

↓

ClinicalDecision

↓

Persistence

LangGraph owns:

• execution order
• retries
• checkpointing
• interrupts
• state recovery

Deliverable:

Deterministic workflow orchestration.

-------------------------------------------------------------------------------
Phase 9 — API Layer
-------------------------------------------------------------------------------

Goal:

Expose the orchestration through FastAPI.

Endpoints:

POST /clinical/ingest

POST /clinical/{thread_id}/approve

GET /clinical/pending

GET /clinical/{case_id}

The API translates HTTP requests into runtime contracts.

It contains no business logic.

Deliverable:

Framework-independent application interface.

-------------------------------------------------------------------------------
Phase 10 — Observability
-------------------------------------------------------------------------------

Goal:

Instrument every architectural boundary.

Examples:

OpenTelemetry

Trace IDs

Checkpoint correlation

Token usage

Retrieval latency

Reasoning latency

Node execution timing

Similarity statistics

Deliverable:

Complete execution visibility.

-------------------------------------------------------------------------------
Phase 11 — Evaluation Framework
-------------------------------------------------------------------------------

Goal:

Measure AI quality independently from software correctness.

Datasets

Golden physician cases

Synthetic scenarios

Regression datasets

Metrics

Top-K Recall

MRR

Prompt comparison

Recommendation agreement

Physician correction rate

Hallucination rate

Retrieval quality

Grounded evidence quality

Deliverable:

Evaluation-driven AI development.

-------------------------------------------------------------------------------
Phase 12 — Testing Strategy
-------------------------------------------------------------------------------

Unit Tests

Deterministic services

Repositories

Utilities

Normalization

Contract validation

Integration Tests

Complete orchestration

Checkpoint recovery

HITL resume

Persistence

Contract invariants

Evaluation

Independent AI benchmarking

Deliverable:

Confidence in both deterministic software and probabilistic AI behaviour.

-------------------------------------------------------------------------------
Phase 13 — Documentation & Architecture
-------------------------------------------------------------------------------

Goal:

Transform the repository into a reference implementation.

Documentation includes:

Architectural Decision Records (ADRs)

Runtime domain language

Business contracts

Processing contracts

Tradeoffs

Security considerations

Evaluation methodology

Failure modes

Recovery strategy

Prompt philosophy

Repository walkthrough

The repository should teach architecture rather than merely present code.

-------------------------------------------------------------------------------
Final Architecture
-------------------------------------------------------------------------------

                          React UI
                              │
                              ▼
                          FastAPI
                              │
                              ▼
                    Runtime Domain Language
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
     Deterministic      CrewAI Reasoning   Persistence
       Services               │            Repositories
             │                ▼                │
             │         PydanticAI             │
             │                │                │
             └──────────── LangGraph ──────────┘
                              │
                 SQLite   Redis   Upstash Vector

Architectural Responsibilities

FastAPI
→ HTTP translation

Runtime Domain Contracts
→ System language

Deterministic Services
→ Business transformations

CrewAI
→ Clinical reasoning

PydanticAI
→ Structured inference

LangGraph
→ Workflow orchestration

SQLite
→ Durable business truth

Redis
→ Deterministic cache

Upstash Vector
→ Semantic candidate retrieval

Observability
→ System introspection

Evaluation
→ AI quality measurement

The architectural centre of AEGIS is not LangGraph, CrewAI, or any individual framework.

The architectural centre is the Runtime Domain Language.

Every framework exists solely to transform, validate, transport, or persist those contracts while preserving deterministic system behaviour.