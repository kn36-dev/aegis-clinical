# Runtime Domain Contract — RetrievalResult

## Purpose

`RetrievalResult` represents the raw semantic retrieval output produced by the retrieval subsystem after querying the configured vector index.

Its responsibility is to faithfully represent which ICD-11 concepts were retrieved as semantically similar to the clinical query. It does not determine diagnosis, clinical relevance, confidence, or final ranking.

`RetrievalResult` is an evidence collection artifact that provides downstream systems with a bounded set of candidate concepts for further deterministic ranking and probabilistic reasoning.

---

## Ownership

**Created by**

- Retrieval service after translating provider-specific vector search output into canonical domain objects.

The underlying vector provider (such as Upstash Vector) is responsible only for executing vector similarity search. It does not own AEGIS domain contracts.

**Consumed by**

- Candidate ranking strategies
- Context assembly
- Evaluation pipelines
- LangGraph workflow state

---

## Lifetime

`RetrievalResult` is an immutable processing artifact.

It is not part of the long-term clinical record and should not be stored as business data.

However, it may be checkpointed inside LangGraph workflow state to support:

- workflow interruption recovery
- HITL resumption
- deterministic replay
- avoiding repeated embedding and retrieval computation

---

## Required Information

Typical fields include:

### Query Reference

A reference to the originating retrieval request or normalized clinical note artifact.

The original clinical content is not duplicated inside the retrieval result.

---

### Retrieval Candidates

A bounded collection of `RetrievalCandidate` objects representing the concepts returned from semantic search.

Each candidate should contain enough information for downstream reasoning without requiring direct dependency on vector infrastructure.

Typical fields:

- `icd_code`
- `title`
- `hierarchy_context`
- `chapter_number`
- `similarity_score`
- `retrieval_metadata`

---

### Retrieval Metadata

Provider-generated metadata required for:

- evaluation
- debugging
- retrieval analysis
- future optimization

Examples:

- similarity distance
- vector namespace
- provider identifiers
- retrieval configuration

---

## Explicit Boundaries

`RetrievalResult` intentionally does **not** contain:

- clinical diagnosis
- confidence score
- physician decision
- LLM reasoning
- final ranking
- ontology interpretation
- ICD selection
- workflow state

A similarity score represents semantic proximity only.

It must never be interpreted as clinical confidence.

---

## Architectural Role

`RetrievalResult` forms the boundary between semantic search infrastructure and downstream reasoning systems.

The retrieval subsystem answers:

"Which concepts are nearby in semantic space?"

It does not answer:

"Which concept is correct?"

Future ranking strategies may consume `RetrievalResult` and produce specialized ranked outputs without modifying the retrieval contract.

This separation enables:

- interchangeable ranking strategies
- retrieval evaluation
- provider replacement
- deterministic debugging
- bounded AI reasoning