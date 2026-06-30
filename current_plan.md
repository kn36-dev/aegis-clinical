# Aegis Clinical — Implementation Roadmap

## Phase 0 — Foundation Cleanup

### Complete

* ✅ Typed application configuration (`config.py`)
* ✅ FastAPI lifespan management
* ✅ SQLite LangGraph checkpointing
* ✅ Dependency injection for:

  * Chat model
  * Upstash Vector
  * Upstash Redis
  * Graph checkpointer

Before continuing:

* Remove the duplicate `get_llm_client()`
* Keep only `get_chat_model()` as the application's LLM dependency.

---

# Phase 1 — Unit Test the Infrastructure

The first goal is proving that the application's infrastructure can be instantiated correctly.

## Files

```
tests/
    api/
        test_dependencies.py

    test_config.py
```

Verify:

* AppSettings loads correctly
* Missing environment variables fail fast
* `get_chat_model()` returns a configured model
* `get_vector_client()` is cached (`lru_cache`)
* `get_redis_client()` is cached
* Graph checkpointer dependency retrieves the lifespan object correctly

At this stage no LLM calls should actually occur.

---

# Phase 2 — Domain Models

Before building the workflow, define every object that flows through it.

## Suggested structure

```
src/aegis/models/

    patient.py

    clinical_note.py

    icd11.py

    workflow.py

    trial.py
```

Examples:

```
ClinicalNote

SymptomExtraction

ICDSuggestion

PhysicianReview

WorkflowState
```

These become the shared contracts across CrewAI, LangGraph and the API.

---

# Phase 3 — Prompt Definitions

Separate prompt engineering from orchestration.

```
src/aegis/prompts/

    symptom_extraction.py

    icd_validation.py

    trial_matching.py
```

Each file exports only prompt templates.

No API calls.

---

# Phase 4 — CrewAI Layer

Now create the reasoning layer.

```
src/aegis/crew/

    agents.py

    tasks.py

    crews.py
```

Initially implement one specialist:

```
ClinicalReasoningCrew

↓

ClinicalReasoningAgent
```

Internally this agent performs:

* symptom extraction
* interpretation
* ICD suggestion preparation

Future specialist agents can later replace portions of this reasoning.

---

# Phase 5 — LangGraph State

Create the workflow state.

```
src/aegis/graph/

    state.py
```

Example state contains:

* case_id
* raw_note
* normalized_note
* embedding
* candidate_icd_codes
* structured_output
* physician_review
* final_codes

---

# Phase 6 — LangGraph Nodes

Implement each workflow step independently.

```
src/aegis/graph/nodes/

    normalize.py

    redis_lookup.py

    embed_note.py

    taxonomy_lookup.py

    crew_reasoning.py

    physician_review.py

    sqlite_write.py

    redis_update.py
```

Each node should have exactly one responsibility.

---

# Phase 7 — Graph Assembly

Connect the nodes.

```
src/aegis/graph/

    builder.py
```

Resulting workflow:

```
Normalize Note

↓

Redis Cache Lookup

↓

Cache Hit?
 ├── Yes → Return Cached Result
 └── No

↓

Embedding Generation

↓

Taxonomy Lookup

↓

CrewAI Clinical Reasoning

↓

Human Review

↓

SQLite Persistence

↓

Redis Cache Update

↓

Return Response
```

---

# Phase 8 — FastAPI Integration

Wire the workflow into the API.

```
src/aegis/api/routers/

    clinical.py
```

Endpoint:

```
POST /clinical/ingest
```

This endpoint should:

* create WorkflowState
* invoke LangGraph
* return the workflow result

---

# Phase 9 — SQLite Repository Layer

Avoid raw SQL inside graph nodes.

```
src/aegis/database/

    repositories/

        patient_repository.py

        icd_repository.py

        review_repository.py
```

Nodes should call repositories instead of executing SQL directly.

---

# Phase 10 — Upstash Layer

Create thin wrappers around the cloud services.

```
src/aegis/vector/

    taxonomy_lookup.py

src/aegis/cache/

    semantic_cache.py
```

These modules encapsulate all external interactions with Upstash Vector and Redis.

---

# Phase 11 — Evaluation Suite

Keep evaluations separate from tests.

```
evals/

    symptom_extraction/

    icd_accuracy/

    regression/

    hallucination/
```

These measure AI quality rather than software correctness.

---

# Phase 12 — Integration Tests

Only after all components exist.

```
tests/

    integration/

        test_clinical_pipeline.py

        test_hitl.py

        test_trial_matching.py
```

These exercise the complete workflow end-to-end.

---

# Final Architecture

```
React

↓

FastAPI

↓

LangGraph

↓

CrewAI

↓

PydanticAI

↓

Groq

↓

SQLite
│
├── Upstash Vector
└── Upstash Redis
```

Each layer owns a single responsibility:

* FastAPI → API surface
* LangGraph → workflow orchestration
* CrewAI → clinical reasoning
* PydanticAI → structured inference
* SQLite → authoritative persistence
* Upstash Vector → semantic taxonomy retrieval
* Upstash Redis → deterministic cache
