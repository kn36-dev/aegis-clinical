# Aegis Clinical — System Architecture V2

## 1. Executive Summary

- Project goals
- Core philosophy
- Architectural principles

---

## 2. High-Level Architecture

- System context
- Major components
- End-to-end data flow

---

## 3. Canonical Domain Language

- Domain models
- Invariants
- Separation of concerns
- WorkflowState

---

## 4. Clinical Ingestion Pipeline

4.1 Clinical Note Reception

4.2 PHI Detection & Redaction

4.3 Normalization

4.4 Cache Lookup

4.5 Retrieval Pipeline

4.6 Candidate Ranking

4.7 Optional Clinical Reasoning

4.8 Structured Validation

4.9 Physician Review

4.10 Persistence

---

## 5. Retrieval Architecture

### Canonical ICD Store

(SQLite)

### Representation Builder

- Title
- Hierarchy
- Prose
- Future representations

### Embedding Pipeline

### Upstash Vector

### Retrieval Service

### Candidate Ranking

### Confidence Gate

---

## 6. Prompt Engineering

- Philosophy
- Prompt assets
- Prompt boundaries
- Structured outputs

---

## 7. LangGraph

- Graph topology
- Nodes
- State transitions
- Checkpointing

---

## 8. Repository Layer

SQLite

Redis

Upstash Vector

---

## 9. Human-in-the-Loop

- Review workflow
- Approval process
- Audit trail

---

## 10. Evaluation

Embedding Representation Evaluation

Retrieval Metrics

Clinical Accuracy Metrics

Latency

Cost

---

## 11. Testing Strategy

Unit Tests

Integration Tests

Prompt Tests

Retrieval Tests

Evaluation Harness

---

## 12. Future Enhancements

Hybrid Retrieval

Multi-Representation Retrieval

LLM-Assisted Re-ranking

Knowledge Graph Integration