# AEGIS Clinical — Conversation Continuation Summary

## Purpose of this document

This document summarizes the architectural decisions, reasoning, and current project state established in this conversation so a fresh context window can continue from the same architectural baseline.

The conversation focused on moving AEGIS from an initial conceptual AI application design into a Principal AI System Architect-level implementation plan.

The key realization:

> Runtime domain contracts are not implementation code. They are the stable business language that defines what the system means before orchestration, services, agents, or infrastructure are implemented.

The next phase is not to immediately write LangGraph/CrewAI code, but to implement the service layer that operationalizes these contracts and provides clean boundaries for orchestration.

---

# Project Identity

## AEGIS Clinical

AEGIS is not primarily an ICD-11 coding product.

The real product being demonstrated:

> Production-grade AI systems engineering discipline.

The clinical domain exists because healthcare naturally requires:

- determinism
- traceability
- human oversight
- reproducibility
- bounded reasoning
- evaluation-driven development

The portfolio objective is that an engineering reviewer sees:

> "This person understands how production AI systems should actually be engineered."

The system demonstrates:

- deterministic workflow orchestration
- bounded LLM reasoning
- retrieval-first architecture
- strict AI output validation
- human-in-the-loop safety
- evaluation-driven AI development
- cost/reliability awareness
- clean ownership boundaries

---

# Current Completed Work

## Offline Knowledge Preparation Pipeline — COMPLETE

Completed:

- WHO ICD-11 dataset analysis
- SQLite taxonomy seeding
- ICD-11 hierarchy reconstruction
- representation builder
- embedding provider abstraction
- local SentenceTransformer embedding support
- OpenAI embedding support
- VectorDocument abstraction
- provider-independent VectorStore interface
- Upstash Vector adapter
- LocalVectorStore
- resumable upload checkpointing
- batch indexing pipeline
- indexing tests

Important correction:

The offline pipeline does NOT repeatedly consult SQLite during embedding.

Actual flow:

```
WHO ICD-11 CSV

        |

SQLite taxonomy seed

        |

RepresentationBuilder

        |

Embedding Provider

        |

Upstash Vector
```

SQLite remains the authoritative taxonomy ledger.

Upstash Vector is the semantic retrieval index.

---

# Storage Philosophy

## SQLite

Role:

Authoritative system of record.

Contains:

- clinical cases
- patient references
- ICD taxonomy
- physician-approved decisions
- workflow checkpoint data

SQLite is where durable truth lives.

---

## Upstash Vector

Role:

Semantic neighborhood retrieval.

It does NOT diagnose.

It does NOT decide.

It does NOT contain mutable application truth.

Its responsibility:

> Given a clinical representation, retrieve nearby ICD concepts.

Current metadata example:

```
{
 "code":"1A00",
 "title":"Cholera",
 "context_path":"Gastroenteritis or colitis of infectious origin → Bacterial intestinal infections → Cholera",
 "chapter_number":"01",
 "representation_type":"structured_prose",
 "embedded_text":"ICD-11 Code: 1A00 Classification Hierarchy..."
}
```

Vector retrieval objective:

High recall.

Not final classification.

---

## Upstash Redis

Role:

Deterministic cache only.

Final design:

```
normalized_note_hash

        |

approved ICD-11 codes
```

Redis must NOT contain:

- LLM recommendations
- uncertain predictions
- CodingRecommendation
- AI reasoning

Only physician-confirmed decisions enter cache.

---

# Core Runtime Architecture Philosophy

Final pipeline:

```
Clinical Note

      |

Anonymization

      |

Normalization

      |

Redis Exact Cache Lookup

      |

(Cache hit)
      |
      v
ClinicalDecision retrieval


(Cache miss)

      |

Embedding

      |

Vector Retrieval

      |

RetrievalResult

      |

Context Assembly

      |

ReasoningContext

      |

CrewAI Clinical Reasoning

      |

PydanticAI Validation

      |

CodingRecommendation

      |

Human Physician Review

      |

ClinicalDecision

      |

SQLite Persistence

      |

Redis Cache Update
```

---

# Why Contracts Were Defined Before Code

Important realization:

The contracts are the architectural vocabulary.

They answer:

- What exists?
- Who creates it?
- Who owns it?
- Who can modify it?
- What does it mean?
- Where is its authority boundary?

They intentionally contain no LangGraph/CrewAI implementation.

This is normal.

Large production systems define domain objects before orchestration.

The next step is implementing services around these contracts.

---

# Final Runtime Domain Contracts

The six original contracts evolved into the following runtime language:

---

# 1. ClinicalNote

## Purpose

Immutable physician-authored clinical observation.

Created by:

Physician → React → FastAPI

Contains:

- patient_id
- case_id
- raw clinical note reference/content

Does NOT contain:

- ICD codes
- AI reasoning
- recommendations

Rules:

- immutable
- one case = one clinical note
- same patient with multiple visits produces multiple notes

Raw PHI handling decision:

Prefer separation through content reference rather than blindly storing plaintext everywhere.

---

# 2. NormalizedClinicalNote

## Purpose

Deterministic derivative used for processing.

Created immediately after ingestion.

Responsible for:

- cache identity preparation
- downstream deterministic processing

Important distinction:

Two normalization paths exist.

## Cache normalization

Aggressive:

- lowercase
- whitespace normalization
- punctuation removal
- deterministic token handling

Purpose:

Increase Redis cache hit probability.

## AI processing normalization

Preserve natural language.

Purpose:

Embedding quality.

Do NOT destroy semantic meaning.

Critical rule:

Normalization must not change meaning.

Example:

```
No fever
```

must never become:

```
fever
```

No LLM-based normalization.

Best effort deterministic negation handling only.

Contains:

- normalized content
- normalization version

Does NOT contain:

- hash

Hash belongs to later processing.

---

# 3. RetrievalRequest

## Purpose

Request semantic retrieval.

Created by:

Retrieval Service.

Contains:

- clinical note reference
- query representation
- retrieval parameters

Does NOT know:

- Redis
- Upstash
- implementation details

It represents:

"What should be retrieved?"

not:

"How retrieval happens?"

---

# 4. RetrievalResult

## Purpose

Raw output of semantic retrieval.

Created by:

Retrieval Service.

Contains:

RetrievalCandidate list.

Does NOT perform ranking.

Does NOT contain confidence.

Uses:

similarity_score

not:

confidence_score

Failure:

Retrieval failure terminates workflow.

No empty fake result.

---

# RetrievalCandidate

Represents:

One ICD taxonomy candidate.

Contains:

- ICD code
- title
- hierarchy
- embedded text
- similarity score
- metadata

One candidate = one ICD code.

No duplicate ICD codes.

Vector IDs are not required.

---

# 5. ReasoningContext

## Purpose

The exact bounded context supplied to probabilistic reasoning.

Created by:

ContextAssembler service.

Contains:

- anonymized clinical note
- curated ICD candidates
- candidate ordering
- context metadata

Does NOT contain:

- prompts
- instructions
- similarity scores

Reason:

Prompt evaluation and context evaluation should remain independent.

The LLM should not see retrieval scores.

---

# Reasoning Boundary

Important clarification:

LangGraph does not disappear.

The architecture should be:

```
LangGraph
    |
    |
    +-- Retrieval Service
    |
    +-- Context Assembly Service
    |
    +-- CrewAI Reasoning Boundary
              |
              |
              LLM
              |
              PydanticAI validation
```

CrewAI is NOT the application orchestrator.

LangGraph owns:

- workflow
- checkpoints
- HITL
- state transitions

CrewAI owns:

- bounded reasoning execution

---

# 6. CodingRecommendation

## Purpose

AI-generated recommendation.

Not truth.

Created by:

LLM reasoning pipeline.

Validated by:

PydanticAI.

Contains:

For each recommended ICD:

```
ICD Code

Supported Findings

Conflicting Findings

Justification

Reasoning Summary
```

Rules:

- must only select retrieved candidates
- cannot invent ICD codes
- can contain multiple candidates
- ranked by LLM opinion

Does NOT enter:

- patient tables
- Redis cache

Stored only:

- LangGraph checkpoint
- evaluation artifacts

---

# 7. ClinicalDecision

## Purpose

Final clinical truth.

Created by:

Backend after physician action.

Physician provides:

approval/modification.

Backend constructs:

ClinicalDecision.

Contains:

- approved ICD codes
- provenance
- decision metadata

Tracks:

- approved recommendation
- physician added
- physician removed

Important:

Physician approves ICD codes only.

They do NOT approve:

- AI reasoning
- evidence
- explanations

---

Rules:

ClinicalDecision:

- immutable
- permanent
- corrections create new decisions

Authority:

Only ClinicalDecision creates durable clinical truth.

---

# Database Design Insight

Existing:

```
patient_extracted_code
```

can represent the durable approved codes.

However:

Need to distinguish:

AI recommendation:

NOT here.

Physician decision:

YES here.

Potential improvement:

Add source/provenance fields.

Example:

```
extraction_source

PHYSICIAN_APPROVED
AI_RECOMMENDATION
```

but only physician-approved records become trusted outputs.

---

# Important Architectural Decision

## Should AI auto-approve high confidence cases?

Final leaning:

Avoid poisoning the golden dataset.

The system should initially prefer:

```
AI Recommendation

        |

Human Approval

        |

ClinicalDecision

        |

Redis Cache
```

Reason:

The golden dataset is the foundation of future evaluation.

If AI-generated decisions enter it:

- evaluation becomes contaminated
- cache becomes polluted
- errors become amplified

Future optimization can introduce:

"trusted automation tiers"

but only after evaluation proves reliability.

---

# Current Missing Layer

After contracts, the next missing abstraction is:

# Service Layer

Contracts define:

"What exists."

Services define:

"How the system causes these things to exist."

Expected services:

```
src/aegis/services/

    clinical_note_service.py

    normalization_service.py

    retrieval_service.py

    context_assembly_service.py

    reasoning_service.py

    decision_service.py

    cache_service.py

    persistence_service.py
```

---

# Expected Service Responsibilities

## NormalizationService

Creates:

NormalizedClinicalNote


## RetrievalService

Consumes:

RetrievalRequest

Produces:

RetrievalResult


## ContextAssembler

Consumes:

ClinicalNote

+

RetrievalResult

Produces:

ReasoningContext


## ReasoningService

Consumes:

ReasoningContext

Produces:

CodingRecommendation


## DecisionService

Consumes:

CodingRecommendation

+

Physician input

Produces:

ClinicalDecision


## PersistenceService

Consumes:

ClinicalDecision

Writes:

SQLite


## CacheService

Consumes:

ClinicalDecision

Writes:

Redis

---

# Current Development Position

Completed:

```
Database design
        |
        v
Offline indexing
        |
        v
Runtime domain contracts
```

Next:

```
Service layer implementation
        |
        v
LangGraph orchestration
        |
        v
CrewAI integration
        |
        v
Prompt engineering
        |
        v
Evaluation harness
```

---

# Important Mental Model Going Forward

Do NOT think:

"Now I need to write LangGraph."

Think:

"I need to make every state transition in LangGraph call a well-defined service that produces a well-defined contract."

LangGraph should become thin.

The intelligence belongs in:

- services
- reasoning boundary
- evaluation framework

The graph only coordinates.

---

# Recommended Immediate Next Conversation

Start by designing:

## AEGIS Service Layer Architecture

Questions to answer:

1. What services exist?
2. Which contract does each service create?
3. Which dependencies does each service own?
4. What failures can each service produce?
5. What belongs inside LangGraph nodes versus services?
6. Where does CrewAI begin and end?

After that:

Implement LangGraph orchestration confidently.