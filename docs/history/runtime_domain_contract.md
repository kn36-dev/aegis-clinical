> ⚠️ **HISTORICAL / SUPERSEDED SNAPSHOT.** This is a point-in-time architectural summary
> from just after offline knowledge compilation, when runtime orchestration had not yet
> been built. Its "Ready to Begin Runtime Orchestration" framing no longer reflects the
> system — the LangGraph workflow is now fully wired. It also duplicates higher-authority
> sources. For current truth see `domain_contract_finalized.md` and
> `runtime_domain_contracts/` (authoritative), and `docs/orchestration.md`. Retained for
> historical/portfolio context only.

# AEGIS Clinical — Architectural Summary & Design Decisions
Version: Runtime Domain Language Complete
Status: Ready to Begin Runtime Orchestration (LangGraph + CrewAI)

================================================================================
PROJECT PHILOSOPHY
================================================================================

AEGIS is NOT primarily an ICD-11 coding assistant.

The clinical domain exists because it naturally requires:

- deterministic execution
- auditability
- traceability
- bounded AI reasoning
- Human-in-the-Loop (HITL)
- reproducibility

The real product being demonstrated is:

    Production-grade AI Systems Engineering.

The intended audience is a Principal Engineer / AI Engineering hiring manager.

Every architectural decision should reinforce this narrative.

The repository should communicate:

"I understand how trustworthy AI systems should actually be engineered."

NOT

"I know how to call an LLM API."

================================================================================
OVERARCHING ENGINEERING PRINCIPLES
================================================================================

Throughout the architectural discussions we converged on several principles.

1. Deterministic systems own workflow.

2. AI never owns workflow.

3. AI only performs bounded reasoning.

4. Human decisions create business truth.

5. Retrieval narrows the search space.

6. LLM compares candidates instead of inventing diagnoses.

7. Everything important becomes testable.

8. Every responsibility belongs to exactly one subsystem.

================================================================================
HIGH-LEVEL RUNTIME FLOW
================================================================================

Clinical Note
      │
      ▼
ClinicalNote
      │
      ▼
Anonymization
      │
      ▼
NormalizedClinicalNote
      │
      ├──────────────┐
      │              │
      ▼              ▼
SHA256 Hash      Embedding
      │              │
      ▼              ▼
Redis Cache   Upstash Vector
                     │
                     ▼
RetrievalResult
                     │
                     ▼
ContextAssembler
                     │
                     ▼
ReasoningContext
                     │
                     ▼
CrewAI
                     │
                     ▼
LLM
                     │
                     ▼
CodingRecommendation
                     │
                     ▼
Physician Review
                     │
                     ▼
ClinicalDecision
                     │
      ┌──────────────┴──────────────┐
      ▼                             ▼
SQLite                      Redis Cache

================================================================================
OFFLINE KNOWLEDGE COMPILATION
================================================================================

This architecture was refined significantly.

Original misconception:

SQLite
      │
      ▼
RepresentationBuilder
      ▼
SQLite again
      ▼
Embedding

Final architecture:

WHO ICD-11 CSV

↓

SQLite

(simple hierarchy reconstructed using ">")

↓

RepresentationBuilder

↓

Embedding Provider

↓

Upstash Vector

The RepresentationBuilder DOES NOT query SQLite again.

SQLite is only seeded once.

The embedding pipeline consumes the representation directly.

================================================================================
VECTOR DATABASE PHILOSOPHY
================================================================================

Initially there was discussion around enriching ICD entries with symptoms.

This was rejected.

Reasons:

- creates unofficial medical ontology
- difficult to validate
- impossible to maintain
- hurts reproducibility
- conflicts with deterministic philosophy

Final decision:

Vector Search is NOT a diagnosis engine.

Its job is only:

"Find the closest neighborhood of ICD concepts."

The LLM becomes the comparison engine.

================================================================================
FINAL RETRIEVAL PHILOSOPHY
================================================================================

Physician Note

↓

Embedding

↓

Top-K ICD Retrieval

↓

Candidate Comparison

↓

Human Approval

NOT

Physician Note

↓

LLM

↓

Entire ICD Database

The retrieval layer performs candidate generation only.

The LLM performs constrained comparison only.

================================================================================
SQLITE VS VECTOR RESPONSIBILITIES
================================================================================

SQLite owns:

- business truth
- ICD taxonomy
- patient cases
- physician decisions
- workflow state
- audit history

Upstash Vector owns:

semantic nearest-neighbor retrieval only.

Redis owns:

exact deterministic cache.

================================================================================
RUNTIME DOMAIN LANGUAGE
================================================================================

We converged on six canonical runtime contracts.

Business Domain

- ClinicalNote
- ClinicalDecision

Processing Artifacts

- NormalizedClinicalNote
- RetrievalRequest
- RetrievalResult
- ReasoningContext
- CodingRecommendation

Workflow

LangGraph State

These contracts intentionally do NOT depend on:

- LangGraph
- CrewAI
- SQLite
- Upstash
- Redis

They represent business language.

Frameworks consume them.

================================================================================
CLINICALNOTE
================================================================================

Immutable physician observation.

Contains:

- case_id
- patient reference
- content reference

Does NOT contain:

- ICD codes
- AI output

Original note never changes.

================================================================================
NORMALIZEDCLINICALNOTE
================================================================================

Generated immediately after ingestion.

Purposes:

- PHI-safe application artifact
- deterministic preprocessing

Important decision:

Two normalization pipelines exist.

Pipeline A

Natural language normalization

↓

Embedding

Pipeline B

Aggressive cache normalization

↓

Redis hash

Stop-word removal ONLY belongs to Redis pipeline.

Never remove stop words before embedding.

Hash computation is NOT part of this contract.

Normalization version is stored.

================================================================================
RETRIEVALREQUEST
================================================================================

Technology-agnostic request.

Contains:

- reference to ClinicalNote
- retrieval parameters

Knows nothing about:

- Redis
- Upstash
- embedding provider

================================================================================
RETRIEVALRESULT
================================================================================

Pure output of retrieval.

Contains:

RetrievalCandidates

Each candidate contains:

- ICD code
- embedded representation
- metadata
- similarity score

Important decisions:

- similarity ≠ confidence
- no ranking beyond retrieval
- no ontology reasoning
- no confidence
- retrieval failure terminates workflow

================================================================================
REASONINGCONTEXT
================================================================================

Created by ContextAssembler.

Contains:

- ClinicalNote
- curated RetrievalCandidates

Does NOT contain:

- prompts
- instructions
- similarity scores

Ordering is preserved.

LLM never sees similarity score.

ReasoningContext is checkpointed.

Context assembly remains independent from LangGraph.

================================================================================
CODINGRECOMMENDATION
================================================================================

Purpose:

Clinical Note

+

Retrieved ICD Concepts

↓

AI Recommendations

Important decisions:

LLM may ONLY choose from retrieved candidates.

Never invent ICD codes.

Recommendation contains:

- ICD code
- structured evidence
- supporting findings
- conflicting findings
- justification
- reasoning summary

Pydantic validates everything.

Recommendation never creates business truth.

Recommendation is checkpointed.

Never persisted as clinical truth.

Never enters Redis.

================================================================================
CLINICALDECISION
================================================================================

Highest authority.

Backend constructs it.

Physician supplies approval.

Tracks:

Approved

Added

Removed

ClinicalDecision creates durable truth.

Only ClinicalDecision may trigger:

SQLite persistence

Redis write-back

ClinicalDecision is immutable.

Corrections create new ClinicalDecision.

================================================================================
CACHE PHILOSOPHY
================================================================================

Redis stores ONLY

normalized_hash

↓

approved ICD codes

Nothing else.

Never:

- recommendations
- evidence
- reasoning
- confidence

Only physician-approved truth.

================================================================================
HALLUCINATION DEFENSE
================================================================================

Three defensive layers.

Layer 1

Retrieval limits candidate space.

Layer 2

LLM may only choose retrieved codes.

Layer 3

Pydantic validates output.

Layer 4

ClinicalDecision required before persistence.

Hallucinated ICD codes therefore cannot reach production.

================================================================================
CREWAI PHILOSOPHY
================================================================================

Current implementation intentionally uses ONE agent.

Reason:

CrewAI establishes the reasoning boundary.

Not because multiple agents are needed.

Future agents can be added without changing LangGraph.

================================================================================
LANGGRAPH PHILOSOPHY
================================================================================

LangGraph owns:

- orchestration
- retries
- checkpointing
- HITL pause
- state recovery

CrewAI owns:

reasoning.

PydanticAI owns:

structured validation.

The frameworks are intentionally separated by responsibility.

================================================================================
EVALUATION PHILOSOPHY
================================================================================

Traditional tests verify deterministic software.

Evaluation verifies AI behavior.

Important future metrics:

Top-K Recall

MRR

Prompt comparison

Retrieval quality

Grounded evidence

Hallucination rate

Recommendation vs physician agreement

Physician corrections

Evaluation is a first-class architectural concern.

================================================================================
IMPORTANT REALIZATION
================================================================================

The runtime contracts are NOT LangGraph models.

They are NOT database schemas.

They are NOT API DTOs.

They are the ubiquitous runtime language of AEGIS.

LangGraph,

CrewAI,

PydanticAI,

FastAPI,

SQLite,

Redis,

Vector Search,

Evaluation,

Observability

all communicate through this language.

Because of this, any individual framework can later be replaced without changing the business domain.

================================================================================
NEXT PHASE
================================================================================

The runtime language is considered complete.

The next architectural phase is NOT writing application code.

It is designing how LangGraph orchestrates these contracts.

The graph should now be defined entirely in terms of transitions between the runtime contracts:

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

Only after the orchestration topology is finalized should implementation of LangGraph nodes, CrewAI agents, prompt engineering, and PydanticAI models begin.

The contracts now form the stable foundation upon which the remainder of AEGIS will be built.