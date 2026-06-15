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
* **State Checkpointing:** Employs persistent, transaction-aware memory checkpointers allowing concurrent execution threads to save state at every step, protecting against system failures mid-trial.

### 2. `aegis.schemas` (Type-Safe Edge Guarding)
* **Defensive PydanticAI Layer:** Enforces strongly typed schemas on unstructured text generation. Uses Python type hints and model validators to inspect raw LLM outputs, converting them into structured objects while stripping away unvalidated escapes, hanging control characters, or malicious prompt injections.
* **PII Anonymization Pipeline:** A high-throughput scrubbing module that identifies and masks protected health information (PHI) before any text payload reaches an external LLM provider.

### 3. `aegis.agents` (Concurrent Taxonomy Mapping)
* **Colloquial-to-ICD-11 Conversion:** Orchestrates a CrewAI worker pool that takes ambiguous, patient-written statements and matches them with exact, hierarchically correct international classification numbers.
* **Concurrent Tool Execution:** Agents utilize asynchronous external tools to hit validation registries concurrently, enriching the state context without blocking execution loops.

### 4. `aegis.hitl` (Asynchronous Physician Sign-Off)
* **Interrupt and Resume Subsystem:** Implements state-level pausing. When a patient-to-trial match score crosses safety thresholds, the engine securely freezes the execution path, generates an immutable resume token, and registers an alert for a physician.
* **State Hydration:** Re-hydrates and resumes processing threads identically from the exact point of interruption upon receiving a cryptographic signature from a qualified reviewer.

---

## 🧪 "Proof of Competence" Evaluation Framework

Medical AI systems demand empirical verification. `aegis-clinical` treats evaluation data as first-class code citizens within the `evals/` framework.

| Pillar | Focus Vector | The Verification Metric / Proof |
| :--- | :--- | :--- |
| **State Chart Determinism** | Path Invariance | Running 1,000 randomized parallel execution requests simulating sudden tool errors, rate-limiting, and bad payloads. LangGraph must prove **100% path compliance**—zero illegal node transitions or state leaks. |
| **Schema Integrity** | Adversarial Boundary Fuzzing | Injecting malicious, broken, or deeply nested adversarial strings into the PydanticAI boundary via `Hypothesis`. The validation layers must prove **100% catchment/rejection** of harmful inputs, never passing a corrupted primitive downstream. |
| **Clinical Taxonomy Accuracy** | ICD-11 Alignment Precision | Evaluating the system against a gold-standard cohort of 500 synthetic patient cases. The CrewAI parsing network must demonstrate an **ICD-11 extraction F1-score of $\ge 0.94$**, backed by live verification reports in the testing console. |
| **HITL Persistence** | Token Stability Under Load | Inducing a system-wide restart while 100 threads are actively suspended at a physician sign-off step. The system must prove **100% recovery fidelity**, resuming each thread from its checkpoint token without memory leaks or data loss. |

---

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