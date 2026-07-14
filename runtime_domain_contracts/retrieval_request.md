# Runtime Domain Contract — RetrievalRequest

## Purpose

`RetrievalRequest` represents the deterministic request to the semantic retrieval subsystem. It encapsulates everything required for runtime candidate retrieval while remaining independent of any particular embedding model, vector database, or caching technology.

The purpose of this contract is to establish a stable boundary between deterministic preprocessing and semantic retrieval. It expresses *what* should be retrieved without exposing *how* retrieval is implemented.

---

## Ownership

**Created by**

- Retrieval service after deterministic preprocessing.

**Consumed by**

- Embedding provider
- Retrieval provider

The `RetrievalRequest` should never contain provider-specific implementation details or business workflow state.

---

## Lifetime

The object is immutable and ephemeral.

It exists only during runtime processing and may be checkpointed by the orchestration layer to avoid recomputation. It is not considered part of the application's long-term business record.

---

## Required Information

The contract should contain only the information necessary to perform semantic retrieval.

Typical fields include:

- `clinical_note`
  - Reference to the originating immutable `ClinicalNote`.

- `normalized_note`
  - The deterministic normalized representation used as the semantic query.

The request intentionally omits implementation-specific artifacts such as embeddings, vector identifiers, provider payloads, or cache technology details.

---

## Explicit Boundaries

`RetrievalRequest` intentionally does **not** contain:

- embedding vectors
- Redis keys
- cache lookup results
- Upstash payloads
- vector identifiers
- similarity scores
- retrieval candidates
- workflow state

Those are produced or consumed by downstream retrieval infrastructure.

---

## Architectural Role

`RetrievalRequest` forms the stable contract between deterministic preprocessing and semantic retrieval.

It allows retrieval providers to evolve independently from the rest of the application while ensuring the domain remains unaware of embedding generation, vector search implementation, or infrastructure-specific concerns.

Every semantic retrieval operation within AEGIS should originate from a `RetrievalRequest`, making it the canonical input to the retrieval subsystem.