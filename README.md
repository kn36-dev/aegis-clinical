# aegis-clinical 🛡️

### High-Stakes Clinical Trial Matching Architecture & Orchestration Engine

`aegis-clinical` is a production-grade, deterministic multi-agent orchestration system engineered for high-stakes medical informatics. The platform safely processes unstructured, colloquial clinical notes, maps them to structured medical taxonomies (ICD-11), executes automated validation lookups, and safely routes matches through an asynchronous Human-in-the-Loop (HITL) physician sign-off workflow.

This repository demonstrates **Staff-level AI Systems Engineering**, prioritizing structural determinism, immutable data boundaries, rigorous evaluation harnesses, and bulletproof state-machine topologies over fragile, prompt-dependent agent loops.

---

## 🏗️ Architectural Core & State Topology

Unlike naive agent frameworks that suffer from execution drift, `aegis-clinical` segregates non-deterministic LLM parsing into strictly bounded sub-graphs, governed by a rigid, immutable macro state chart.

* **Macro-Orchestration (LangGraph):** Drives the primary state machine. Implements explicit sequence alignment rules ensuring a patient payload cannot bypass data anonymization, verification, or HITL checkpoints.
* **Specialized Worker Sub-Graphs (CrewAI):** Encapsulates parallel parsing teams. Runs concurrent workers that extract colloquial descriptions, map them to standardized ICD-11 criteria, and run verification lookups against official medical databases.
* **Immutable Data Boundaries (PydanticAI):** Acts as the system’s deep-defensive type-guard. Enforces strict schema validations at the edge, trapping unvalidated text, malicious injections, or corrupted string escapes before they can propagate down to database drivers.

---

## 🛠️ 2026 Tooling & Enterprise Engineering Stack

* **Runtime:** Python 3.13+ managed deterministically via [`uv`](https://github.com/astral-sh/uv).
* **Framework Layer:** LangGraph (State management & checkpointers), PydanticAI (Type-safe LLM boundaries), CrewAI (Dynamic agent worker pools).
* **Observability & Evaluation:** OpenTelemetry for distributed tracing and core telemetry collection; BrainTrust for production-grade evaluation and regression tracking.
* **Storage & Persistence:** SQLite configured for transactional checkpointing; Redis for distributed state cache and consistency management.
* **Quality Assurance & Lints:** `ruff` enforcing strict enterprise formatting and security profiles (`E`, `F`, `B`, `ASYNC`, `TCH`). `mypy` running with `strict = true`.
* **Evaluation & Testing:** `pytest` paired with custom LLM-as-a-judge evaluation frameworks to systematically score extraction precision, recall, and state transition invariance.

---

## 📂 Repository Architecture

```text
aegis_clinical/
├── .github/workflows/          # CI/CD: Strict lint, type checks, and evaluation suites
├── .devcontainer/              # Standardized medical-grade development environment
├── data/                       # Mock clinical datasets (100% synthetic, HIPAA-compliant)
├── evals/                      # The Evaluation Harness (System accuracy metrics)
│   ├── test_icd11_precision.py # Extraction precision/recall benchmarks
│   └── test_state_invariance.py# State drift and adversarial transition testing
├── src/
│   └── aegis/                  # Core application package
│       ├── __init__.py
│       ├── agents/             # CrewAI sub-graphs and tool definitions
│       │   ├── parsing.py      # Colloquial symptom extraction workers
│       │   └── lookup.py       # ICD-11 official terminology verifiers
│       ├── graphs/             # LangGraph state-chart topologies
│       │   ├── state.py        # Shared thread-safe context schema
│       │   └── workflow.py     # Deterministic state routing logic
│       ├── schemas/            # PydanticAI structured output parameters
│       │   ├── anonymizer.py   # PII scrubbing models
│       │   └── validation.py   # Immutable schema type-guards
│       └── hitl/               # Human-in-the-Loop synchronization mechanics
│           ├── storage.py      # Thread checkpoint and persistence state engines
│           └── router.py       # Interrupted run suspension and resume tokens
├── tests/                      # Core Unit & Integration Suite
│   ├── unit/
│   └── integration/            # End-to-end verification loops
├── pyproject.toml              # Project dependencies and tool settings via uv
└── README.md
```

---

## 📦 Detailed Module Implementations

### 1. `aegis.graphs` (Deterministic State Charts)
* **Sequence Alignment Enforcement:** Builds a LangGraph topology that maps the entire trial matching lifecycle. Implements conditional edges that strictly verify node success flags, entirely preventing downstream evaluation if prior stages (such as anonymization) fail or time out.
* **Phase 5 Clinical Review Checkpoints:** Uses LangGraph `interrupt_before` mechanics to freeze execution before moving into clinical matching confirmation, requiring affirmative human sign-off.
* **CrewAI Fault Isolation:** Traps inner agent failures and processes worker runtime exceptions cleanly, transitioning the graph execution explicitly into a `FAILED` state instead of causing macro-graph hanging or thread deadlocks.
* **State Checkpointing:** Employs persistent, transaction-aware memory checkpointers allowing concurrent execution threads to save state at every step, protecting against system failures mid-trial.

### 2. `aegis.schemas` (Type-Safe Edge Guarding)
* **Defensive PydanticAI Layer:** Enforces strongly typed schemas on unstructured text generation. Uses Python type hints and model validators to inspect raw LLM outputs, converting them into structured objects while stripping away unvalidated escapes, hanging control characters, or malicious prompt injections.
* **Negation Semantic Validation Guard:** Intercepts LLM extraction arrays to explicitly protect against semantic inversion. The guard acts as a high-fidelity logical validation gate ensuring clinical assertions (e.g., "no diabetes") cannot be corrupted or falsely transformed into an active diagnosis flag (e.g., "diabetes present").
* **PII Anonymization Pipeline:** A high-throughput scrubbing module that identifies and masks protected health information (PHI) before any text payload reaches an external LLM provider.

### 4. `aegis.hitl` (Asynchronous Physician Sign-Off)
* **Interrupt and Resume Subsystem:** Implements state-level pausing. When a patient-to-trial match score crosses safety thresholds, the engine securely freezes the execution path, generates an immutable resume token, and registers an alert for a physician.
* **Optimistic Locking & State Versioning:** Enforces strict data concurrency via state version tokens. The system compares incoming interaction payloads against current DB versioning snapshots, systematically rejecting stale updates when versions differ.
* **Stale Update Handling & Token Expiration:** Manages token expiration handling during exceptionally long-running review workflows. If an expired or out-of-date token submission occurs, the router rejects the update, returns an HTTP `409 Conflict` response, and mandates an absolute client-side UI refresh.
* **State Hydration:** Re-hydrates and resumes processing threads identically from the exact point of interruption upon receiving a cryptographic signature from a qualified reviewer.

## 🧪 "Proof of Competence" Evaluation Framework

Medical AI systems demand empirical verification. `aegis-clinical` treats evaluation data as first-class code citizens within the `evals/` framework.

| Pillar | Focus Vector | The Verification Metric / Proof |
| :--- | :--- | :--- |
| **State Chart Determinism** | Path Invariance | Running 1,000 randomized parallel execution requests simulating sudden tool errors, rate-limiting, and bad payloads. LangGraph must prove **100% path compliance**—zero illegal node transitions or state leaks. |
| **Schema Integrity** | Adversarial Boundary Fuzzing | Injecting malicious, broken, or deeply nested adversarial strings into the PydanticAI boundary via `Hypothesis`. The validation layers must prove **100% catchment/rejection** of harmful inputs, never passing a corrupted primitive downstream. |
| **Semantic Inversion Guard** | Negation Reversal Prevention | Asserting deterministic semantic invariants via a targeted test suite. The system must maintain a **0% leak rate** on inverted negation expressions (e.g., proving "no diabetes" never converts to true). |
| **Clinical Taxonomy Accuracy** | ICD-11 Alignment Precision | Evaluating the system against a gold-standard cohort of 500 synthetic patient cases. The CrewAI parsing network must demonstrate an **ICD-11 extraction F1-score of $\ge 0.94$**, backed by live verification reports in the testing console. |
| **HITL Persistence** | Token Stability Under Load | Inducing a system-wide restart while 100 threads are actively suspended at a physician sign-off step. The system must prove **100% recovery fidelity**, resuming each thread from its checkpoint token without memory leaks or data loss. |
| **Concurrency Safeguards** | Optimistic Conflict Resolution | Injecting race-condition updates with mismatched version tokens. The engine must maintain **100% precise rejections**, returning an HTTP `409 Conflict` code across all parallel collisions. |
| **Continuous Regression Tracking** | BrainTrust Platform Validation | Running automated evaluation workflows integrated with BrainTrust to visualize precision shifts, tracking score histories over time to capture and prevent model behavior regressions. |

## 🚀 Production-Grade CI/CD Pipeline Gates

The system relies on an automated, zero-trust integration workflow defined in `.github/workflows/` to guard main branch purity. Code changes are barred from deployment unless they successfully satisfy five structural gates:

1. **Static Analysis & Formatting Rules:** Continuous execution of `ruff check .` to enforce programmatic formatting, clean async practices, and strict type placement.
2. **Strict Type-Safety Verification:** Complete verification of codebase dependencies via `mypy src/` enforcing `strict = true` compliance across all operational components.
3. **Core Functional Verification:** Execution of standard unit and integration test sweeps via `pytest tests/` to confirm basic logic, error traps, and network routing boundaries.
4. **Automated AI Performance Evaluation:** Systematic execution of the `evals/` cohort inside specialized CI runners, automatically pushing telemetry traces to BrainTrust and OpenTelemetry collectors. Any performance drop below established thresholds flags an instant deployment block.
5. **Continuous Deployment Gateways:** Automated deployment tasks are unlocked only when code quality validation metrics, security linting, and LLM-as-a-judge accuracy benchmarks are successfully met.

## ⚡ Setup & Execution

### Prerequisites
* `uv` package manager installed globally.
* Environment keys loaded: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`.

### 1. Initialize and Install Dependencies
```bash
uv sync --all-groups
```

### 2. Execute Code Quality & Static Typing Verifications
```bash
uv run ruff check .
uv run mypy src/
```

### 3. Run Core Functional and Integration Tests
```bash
uv run pytest tests/
```

### 4. Execute the High-Stakes Clinical Evaluation Harness
```bash
uv run pytest evals/ -v --tb=short
```

### 5. Distributed Consistency & System Reliability
* **High-Performance Storage Configuration:** Optimizes the embedded persistence tier using SQLite Write-Ahead Logging (`journal_mode=WAL` and `synchronous=NORMAL`) to assure scalable, parallel read/write capabilities under production thread pressures.
* **Dual-Write Concurrency & Transactional Integrity:** Leverages native `asyncio.gather()` configurations to achieve non-blocking, simultaneous updates across downstream nodes.
* **Eventual Consistency Architecture:** Synchronizes concurrent Redis cache additions and Vector database indexes by implementing structured Saga, Outbox, or compensating-transaction design patterns, mathematically assuring complete eventual consistency across isolated storage engines.


The system will be cheaper overtime with 
`Deterministic Hash → Vector Proximity → Agentic LLM` flows defined in clinical_note_ingestion_flow.md

RESUME DESCRIPTION:
TECHNICAL AI PORTFOLIO
High-Stakes Clinical Trial Matching Architecture | LangGraph & PydanticAI
Engineered a deterministic clinical state chart via LangGraph to guarantee sequence alignment across data anonymization, multi-agent parsing, and asynchronous HITL physician sign-off. 
Orchestrated specialized agent sub-graphs using CrewAI to autonomously parse colloquial symptoms into structured ICD-11 codes while concurrently driving validation lookups.
Leveraged PydanticAI to enforce rigid runtime validation boundaries on unstructured text notes, eliminating unvalidated string escapes from penetrating downstream databases.
Technologies: Advanced Python Archetypes, Asynchronous Concurrency, State-Machine Topology, Schema Enforcement, Human-in-the-Loop Orchestration.

"the system becomes more efficient over time through deterministic caching." (current implementation)
"the system can be extended to leverage accumulated physician-reviewed cases as institutional semantic memory." (future enhancement)