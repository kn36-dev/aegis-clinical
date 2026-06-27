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