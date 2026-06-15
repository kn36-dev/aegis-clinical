aegis-clinical/
├── .devcontainer/                  # Standardized medical-grade container configuration
├── .github/workflows/              # CI/CD: Strict ruff lints, mypy static checks, and eval gates
│   ├── lint_and_typecheck.yml
│   └── evaluation_harness.yml
│
├── data/                           # Ingress, storage, and taxonomy seeding layers
│   ├── mock_clinical_cases.json    # 100% synthetic, HIPAA-compliant patient test strings
│   ├── seed_icd11.py               # 5-line automation script to download/convert WHO CSV to SQLite
│   └── clinical_registry.db        # Local SQLite instance holding the flat ICD-11 taxonomy
│
├── evals/                          # The Evaluation Harness (System accuracy metrics)
│   ├── conftest.py                 # Shared LLM-as-a-judge fixtures and client initializations
│   ├── test_icd11_precision.py     # CrewAI extraction precision/recall validation loops
│   ├── test_state_invariance.py    # LangGraph adversarial state transition checks
│   └── test_hitl_recovery.py       # Simulates system crash mid-pause to verify token stability
│
├── frontend/                       # React / Vite / TypeScript Physician Dashboard
│   ├── src/
│   │   ├── api/                    # Axios/Fetch clients communicating with the FastAPI backend
│   │   │   └── client.ts
│   │   ├── components/             # Reusable UI elements
│   │   │   ├── DiffViewer.tsx      # Highlights original note vs. AI extracted ICD-11 taxonomy
│   │   │   └── PatientRow.tsx      # Individual patient card showing matching metrics
│   │   ├── hooks/                  # Custom hooks tracking active websocket/polling threads
│   │   │   └── usePendingReviews.ts
│   │   ├── views/                  # Primary layouts
│   │   │   ├── Dashboard.tsx       # Main clinical queue overview
│   │   │   └── ReviewConsole.tsx   # Deep-dive screen where doctors sign off on a match
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json
│   └── tsconfig.json
│
├── src/
│   └── aegis/                      # Core backend application package
│       ├── __init__.py
│       │
│       ├── agents/                 # Concurrent Taxonomy Workers (CrewAI)
│       │   ├── __init__.py
│       │   ├── lookup.py           # Executes concurrent SQLite verifications for extracted codes
│       │   └── parsing.py          # Workers parsing raw, colloquial syntax notes
│       │
│       ├── api/                    # System Ingress Layer (FastAPI Engine)
│       │   ├── __init__.py
│       │   ├── dependencies.py     # Fast injection patterns for database handles & state stores
│       │   ├── main.py             # App initialization, CORS management, and error handshakes
│       │   └── routers/
│       │       ├── clinical.py     # Endpoints receiving notes and kicking off LangGraph runs
│       │       └── review.py       # Endpoints managing physician approvals and resume steps
│       │
│       ├── database/               # Data Access Layers
│       │   ├── __init__.py
│       │   ├── sqlite_client.py    # Handles connections and lookups against clinical_registry.db
│       │   └── vector_client.py    # Interfaces with local ChromaDB/FAISS for semantic RAG data
│       │
│       ├── graphs/                 # Macro-Orchestration Topology (LangGraph)
│       │   ├── __init__.py
│       │   ├── state.py            # Thread-safe context schema holding active patient state
│       │   └── workflow.py         # Linear state routing logic, error handling, and node map
│       │
│       ├── hitl/                   # State Hydration, Tokenization, & Suspension Subsystem
│       │   ├── __init__.py
│       │   ├── router.py           # Handles suspended run generation and token verification
│       │   └── storage.py          # Transaction-aware memory checkpointers mapping back to SQLite
│       │
│       └── schemas/                # Deep-Defensive Edge Type-Guards (PydanticAI)
│           ├── __init__.py
│           ├── anonymizer.py       # PHI scrubbing logic models mapping UUIDs to identity blocks
│           └── validation.py       # Immutable schemas forcing LLM outputs into exact JSON types
│
├── tests/                          # Core functional test suites
│   ├── integration/                # End-to-end integration tests (Ingress to Egress)
│   └── unit/                       # Unit isolation tests for schemas, routers, and utils
│
├── .gitignore
├── pyproject.toml                  # Application settings, lints (ruff, mypy), managed via uv
├── README.md                       # Comprehensive infrastructure setup instructions
└── uv.lock                         # Deterministic lock file tracking backend dependencies