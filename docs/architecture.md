aegis-clinical/
├── .devcontainer/
├── .github/workflows/
│   ├── lint_and_typecheck.yml
│   └── evaluation_harness.yml  # Executes Braintrust CI/CD evaluation suites
├── data/
│   ├── mock_clinical_cases.json
│   ├── seed_icd11.py
│   └── clinical_registry.db
├── evals/
│   ├── conftest.py             # Instantiates Braintrust clients & OpenTelemetry tracers
│   ├── braintrust_judges.py    # Custom LLM-as-a-judge scoring criteria definitions
│   ├── test_icd11_precision.py # CrewAI extraction precision metrics evaluated via Braintrust
│   ├── test_state_invariance.py
│   └── test_hitl_recovery.py
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
├── src/
│   └── aegis/
│       ├── __init__.py
│       ├── agents/
│       │   ├── lookup.py
│       │   └── parsing.py
│       ├── api/
│       │   ├── dependencies.py
│       │   ├── telemetry.py    # Configures global OpenTelemetry span processors & tracer providers
│       │   ├── main.py         # Injects FastApi instrumentation middleware
│       │   └── routers/
│       ├── database/
│       │   ├── state.py        # Engine initialization & WAL configuration
│       │   ├── models.py       # Model schemas from Pydantic
│       │   └── repository.py   # Clean CRUD / UPSERT functions
│       ├── graphs/
│       │   ├── state.py
│       │   └── workflow.py     # Embeds OTel span trace injections on node entry/exit boundaries
│       ├── hitl/
│       └── schemas/
├── .editorconfig               # Two-line minimalist global enforcement (LF, utf-8)
├── .gitattributes              # Hard repository-level LF and binary file classifications
├── .gitignore
├── pyproject.toml              # Unified Ruff linter, Mypy configurations, and uv workspaces
└── uv.lock