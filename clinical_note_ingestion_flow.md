# SYSTEM ARCHITECTURE SPECIFICATION: AEGIS ARCHITECTURAL FLOW
**Role Context for LLM:** Principal AI System Architect / Senior AI Systems Engineer
**System Objective:** High-throughput, HIPAA-compliant clinical documentation processing, hybrid semantic caching, and multi-agent ICD-11 taxonomy mapping with strict cache-poisoning defenses.

---

## 🏗️ SYSTEM ARCHITECTURE OVERVIEW
The system utilizes a decoupled, stateful graph topology (orchestrated via **LangGraph**) to manage five clear operational phases. It deliberately separates deterministic text processing from probabilistic LLM operations, relying on local compute constraints for security and a **Cache-Aside (Write-Back)** structure to minimize LLM token overhead.

```
[Phase 1: Ingress & Anonymize] ──> [Phase 2: Hybrid Cache Check]
                                              │
                                       (Cache Miss)
                                              ▼
[Phase 5: Cache Write-Back]   <── [Phase 4: HITL Sign-off] <── [Phase 3: CrewAI + State Pause]
```

---

## 🔒 PHASE 1: INGRESS & ANONYMIZATION (PRIVACY FIREWALL)
*Objective: Transform raw clinical prose into a 100% anonymized string before any cloud egress or embedding steps occur. This phase preserves grammatical syntax for downstream local NLP parsing.*

* **Step 1.1: Deterministic Contextual Regex Loop**
    * **Mechanism:** Extract known structured form metadata (Patient First Name, Last Name, Date of Birth variations) at the API gateway layer. Run an aggressive, case-insensitive string replacement loop wrapped in explicit word boundaries (`\b`) to handle exact character matches with zero probabilistic failure.
* **Step 1.2: Microsoft Presidio Local Node (Deterministic & Local NLP)**
    * **Mechanism:** Route text through a completely local instance of Microsoft Presidio Analyzer. 
    * **Engineering Note:** This uses local regular expressions for structural strings (SSNs, phone numbers, emails) paired with a lightweight local spaCy Named Entity Recognition (NER) model running completely on local CPU memory. It operates with zero-token cost and total data privacy to redact unrecognized generic entities (`PERSON`, `LOCATION`).
* **Step 1.3: PydanticAI Edge Guard (Contextual Prose Anonymization - Context Dependent)**
    * **Mechanism:** Pass the pre-scrubbed text to a fast, cheap model (e.g., GPT-4o-mini) using a strict structural schema. Its sole focus is to strip non-structural prose identifiers (e.g., *"lives behind the old mill"*).
    * **Critical Guardrail:** The system prompt explicitly forbids the redaction of clinical environmental exposures or occupational histories (e.g., *"works in a coal mine"*, *"heavy smoker"*), as these are vital diagnostic indicators for accurate downstream ICD-11 classification.
    * **Phase Output:** `Anonymized Clinical Note` (Clean, natural-prose string containing structural redaction tokens).

---

## ⚡ PHASE 2: HYBRID CACHING & OPTIMIZATION (TOKEN GATEKEEPER)
*Objective: Intercept incoming requests to achieve sub-millisecond execution times and absolute token elimination via a tiered, deterministic/semantic cache approach.*

* **Step 2.1: Fast-Path Token Normalization & Deterministic Hashing**
    * **Mechanism:** Take the `Anonymized Clinical Note`, apply aggressive programmatic normalization (lowercase, strip whitespaces, strip punctuation, remove standard stop-words), and sort the remaining unique tokens alphabetically. Run a SHA-256 cryptographic hash on this mangled token string. When normalization happens, it should do what's available in src/aegis/schemas/normalization.py
* **Step 2.2: Tier 1 Cache Lookup (Upstash Redis)**
    * **Mechanism:** Query **Upstash Redis** using the SHA-256 hash string as the key.
    * **Result (HIT):** Return the cached array of validated ICD-11 codes immediately. **Cost: 0 LLM tokens, 0 vector compute cycles.**
    * **Result (MISS):** Proceed to Step 2.3.
* **Step 2.3: Tier 2 Cache Lookup (Semantic Vector Proximity Search)**
    * **Mechanism:** Generate a vector embedding of the **unmangled, natural-prose** `Anonymized Clinical Note` using a commodity model API (e.g., `text-embedding-3-small`). Query the **Upstash Vector** index.
* **Step 2.4: Proximity Thresholding & Local Entity Alignment Guard**
    * **Condition A (Cosine Similarity < 0.985):** Cache Miss. Route text directly to Phase 3.
    * **Condition B (Cosine Similarity ≥ 0.985):** Pull the cached candidate's raw text metadata and run it through a Python **Local Entity Alignment Guard**. This script executes a fast regex check looking for mismatched critical negation modifiers (`no`, `not`, `denies`, `never`, `negative`).
        * *If Negation Check Passes:* Safe semantic match. Return cached ICD-11 array.
        * *If Negation Check Fails:* Unsafe semantic collision detected (e.g., symptom confirmed vs symptom denied). Reject the cache hit and route to Phase 3.
    * The negation guard is custom, but it's possible to be improved using spaCy's NegEx for better quality regex checks.

---

## 🤖 PHASE 3: MULTI-AGENT EXECUTION & STATE PERSISTENCE
*Objective: Execute complex, taxonomic reasoning and safely suspend execution threads during long-lived asynchronous wait times without consuming server resources.*

* **Step 3.1: CrewAI Orchestration Pool**
    * **Mechanism:** Spin up parallel worker agents. They ingest the **unmangled, natural-prose** `Anonymized Clinical Note`. Agents leverage custom Python tools to query a local, read-only **SQLite database** containing the raw ICD-11 taxonomy codes and definitions to produce draft diagnostic mappings.
* **Step 3.2: State Machine Checkpointing & Thread Interruption**
    * **Mechanism:** The workflow is coordinated by **LangGraph**. The entire state object—containing the anonymized note text and the ephemeral CrewAI code suggestions—is serialized and written to a database using a LangGraph checkpointer (`SqliteSaver`).
    * **Engineering Implementation:** The graph declares an explicit `interrupt_before` hook on the Phase 5 node. The system snapshots the state matching a deterministic `thread_id` and terminates the live execution thread, freeing system memory.

---

## 🧑‍⚕️ PHASE 4: HUMAN-IN-THE-LOOP (HITL) AUDIT GATEKEEPER
*Objective: Allow clinician validation while creating a strict firewall against cache poisoning.*

* **Step 4.1: Asynchronous Presentation Layer**
    * **Mechanism:** Render the `Anonymized Clinical Note` alongside the ephemeral, unverified CrewAI code suggestions on the clinician's web dashboard. 
    * **Security Guardrail:** The backend strictly isolates these suggestions. No data mutations are permitted inside the caching databases during this stage.
* **Step 4.2: Clinician Mutation & Sign-Off**
    * **Mechanism:** The clinician audits the diagnostic mapping through the UI interface, making adjustments by either accepting the suggestions directly or adding/removing codes manually.
* **Step 4.3: State Machine Resumption**
    * **Mechanism:** The clinician clicks "Sign Off", sending a POST payload with the finalized, approved codes back to the FastAPI gateway. The gateway matches the `thread_id`, invokes `aupdate_state()` to inject the human-validated data into the graph state, and resumes execution.

---

## 💾 PHASE 5: FINALIZING CACHE & LEDGER (WRITE-BACK)
*Objective: Guarantee cache consistency using only human-verified data mappings to seed the systems for future lookups.*

* **Step 5.1: Asynchronous Write-Back Task**
    * **Mechanism:** The graph execution steps into the finalized node, triggering a concurrent background task via `asyncio.gather()` to update both cache layers:
        1.  **Upstash Redis:** Write the normalized SHA-256 hash string key mapped to the human-approved ICD-11 JSON array.
        2.  **Upstash Vector:** Upsert the embedding vector generated from the natural-prose `Anonymized Clinical Note`, embedding the original anonymized prose text and the human-approved code data inside the metadata dictionary.

---

## 🛠️ AI ENGINEERING BOUNDARIES & ANTI-PATTERNS (RABBIT HOLES)
* **Database Scope:** Do not implement a heavy, distributed PostgreSQL architecture or containerized DB clusters. The application layer safely isolates and secures multi-tenant data inside a highly responsive local **SQLite** database configured with **Write-Ahead Logging (WAL)** and application-layer encryption (`cryptography.fernet`) for the identity ledger.
* **Model Layer Limits:** Do not fine-tune custom embedding models or try to train deep neural networks to recognize medical negations. Rely entirely on **commodity embedding layers** bounded by python-native verification code (the Phase 2 Alignment Guard).
* **State Coordination Limits:** Do not attempt to use CrewAI's native interactive human-input prompts over stateless web environments. Treat CrewAI strictly as an ephemeral processing tool inside a deterministic node controlled exclusively by **LangGraph checkpointers**.