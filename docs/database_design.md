## Upstash Vector

Index: aegis_clinical
Embedding Model: text-embedding-3-small
Dimensions: 1536
Similarity Metric: Cosine
Namespace: taxonomy_lookup
Purpose: A read-only semantic index containing embeddings generated from the official ICD-11 taxonomy. The namespace is queried during clinical note ingestion to retrieve the most semantically relevant ICD-11 candidates for downstream AI validation.

Example, note that raw_text is deliberately not included:
ID "1A03"
Dense Vector: 1536-dimensional OpenAI embedding
Metadata: {} (empty)

Embedding Source
Each vector is generated from a concatenated semantic representation of the ICD concept, for example:

ICD Code
1A03
Title
Gastroenteritis or colitis of infectious origin
Description
Inflammatory disease of the gastrointestinal tract caused by infectious organisms...

The stored record remains
id = "1A03"

Lifecycle
ICD11 release -> Generate embeddings once -> Bulk upload -> Read-only afterwards
---

## Upstash Redis

Key: icd_cache:{sha256(normalized_note)}
Type: String
Value: JSON
TTL: 30 days / 90 days (aggressiveness) 

Cache Workflow
Clinical Note -> Normalize -> SHA-256 -> Redis -> ... (2 branches continued)

Cache Hit
Redis -> Cache Hit / Return ICD Codes -> SQLite Audit -> Done

Cache Miss
Redis -> Cache Miss -> Vector Search -> taxonomy_lookup -> CrewAI -> Physician -> SQLite Audit -> Redis Write -> Done


# Planned Database Architecture

The application intentionally follows a **hybrid persistence architecture**, where each storage technology is responsible for a single concern. This minimizes duplicated state, simplifies synchronization, and clearly separates deterministic relational storage from semantic retrieval and transient caching.

---

# SQLite — System of Record

SQLite serves as the authoritative source of truth for all mutable application state.

Responsibilities include:

* Clinical cases
* Physician-approved ICD-11 classifications
* Human-in-the-Loop (HITL) checkpoints
* Audit history
* Optimistic versioning
* LangGraph workflow state
* Complete ICD-11 taxonomy reference

SQLite operates in **Write-Ahead Logging (WAL)** mode to support concurrent readers while preserving transactional consistency. All persistence operations ultimately commit to SQLite before any secondary storage is updated.

---

# Upstash Vector — Semantic Retrieval

Upstash Vector is intentionally treated as a **mathematical nearest-neighbor index**, not as a document database.

A single index contains one namespace:

```text
taxonomy_lookup
```

The namespace stores precomputed embeddings generated from the official ICD-11 taxonomy using OpenAI's `text-embedding-3-small` embedding model.

## Vector Record

| Component | Value                             |
| --------- | --------------------------------- |
| Namespace | `taxonomy_lookup`                 |
| Vector ID | ICD-11 Code (`1A03`, `CA40`, ...) |
| Embedding | 1536-dimensional dense vector     |
| Metadata  | `{}` (empty)                      |
| Raw Text  | Omitted                           |

Example:

```python
index.upsert([
(
    "1A03",
    embedding,
    {}
)
])
```

During ingestion, semantic search returns the nearest ICD-11 identifiers. The application subsequently retrieves the complete taxonomy information from SQLite, preserving SQLite as the single source of truth.

This pointer-based architecture intentionally avoids duplicating mutable metadata inside the vector database.

---

# Upstash Redis — Deterministic Cache

Redis provides a lightweight exact-match cache to eliminate repeated embedding generation and AI inference for identical clinical notes.

Each cache entry is keyed by the SHA-256 hash of a normalized clinical note.

## Cache Record

| Component | Value                                           |
| --------- | ----------------------------------------------- |
| Key       | `icd_cache:{sha256(normalized_note)}`           |
| Type      | String                                          |
| Value     | JSON containing physician-approved ICD-11 codes |
| TTL       | Configurable (for example, 30–90 days)          |

Example:

```json
{
    "codes": [
        "1A03",
        "CA40"
    ],
    "schema_version": 1
}
```

Cache hits immediately return the previously validated ICD-11 codes, bypassing semantic retrieval and AI inference entirely. Cache misses proceed through the normal clinical ingestion pipeline before the resulting physician-approved codes are written back into Redis.

Redis intentionally does **not** store embeddings, workflow state, sessions, or distributed locks within the reference deployment.

---

# Storage Responsibility Matrix

| Storage        | Primary Responsibility                  | Mutable                             |
| -------------- | --------------------------------------- | ----------------------------------- |
| SQLite         | Relational system of record             | Yes                                 |
| Upstash Vector | Semantic retrieval over ICD-11 taxonomy | No (read-only after initialization) |
| Upstash Redis  | Deterministic exact-match cache         | Yes (TTL-managed)                   |

This strict separation ensures every piece of mutable application state exists in exactly one authoritative location while allowing semantic retrieval and caching layers to remain lightweight, disposable projections over the underlying relational data.

---

# Clinical Retrieval Workflow

```text
Clinical Note
      │
      ▼
Normalize
      │
      ▼
SHA-256
      │
      ▼
Redis Cache
 ┌───────────────┐
 │               │
Hit            Miss
 │               │
 ▼               ▼
Return      Generate Embedding
Codes             │
                  ▼
         taxonomy_lookup
                  │
                  ▼
      Candidate ICD-11 Codes
                  │
                  ▼
         CrewAI Validation
                  │
                  ▼
       Physician Approval
                  │
                  ▼
         SQLite Transaction
                  │
                  ▼
        Redis Cache Update
```

---

# Future Evolution

For production deployments processing a sufficiently large corpus of physician-reviewed clinical notes, an additional vector namespace containing embeddings of approved historical cases may be introduced. This semantic institutional memory would enable approximate retrieval of clinically similar historical decisions while SQLite continues to remain the authoritative source of truth.

The reference implementation intentionally omits this optimization because the expected portfolio-scale workload does not justify the additional embedding lifecycle, synchronization logic, or operational complexity.
