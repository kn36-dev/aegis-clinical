.PHONY: dev-backend demo-server dev-frontend lint format test server-check demo

# Run the FastAPI server on our unexcluded port
dev-backend:
	uv run uvicorn aegis.api.main:app --app-dir src --reload --host 0.0.0.0 --port 9000

# Same FastAPI app, same LangGraph workflow, same routers -- only the
# composition root's AEGIS_PROFILE differs, swapping the cache,
# reasoning, and content-repository collaborators for deterministic
# in-memory ones. Embedding + Upstash Vector retrieval stay real. See
# CLAUDE.md's demo-profile design and docs/tradeoffs_and_limitations.md.
demo-server:
	AEGIS_PROFILE=demo uv run uvicorn aegis.api.main:app --app-dir src --reload --host 0.0.0.0 --port 9000

# Run your React frontend (Assuming it sits in a 'frontend' subfolder)
dev-frontend:
	cd frontend && pnpm run dev

# Run all code quality sanitizers sequentially
server-check:
	uv run ruff format
	uv run ruff check
	uv run mypy src

# Runs both front and back concurrently (requires the 'concurrently' or utility runner)
dev-all:
	make -j 2 dev-backend dev-frontend

.PHONY: db-init db-seed-icd

# Creates the clinical registry and graph checkpoint SQLite databases from
# the ordered migrations in src/aegis/database/migration/. Schema only --
# no ICD taxonomy data. Run db-seed-icd afterward to populate retrieval data.
db-init:
	uv run aegis-db init --all --reset

# Populates icd11_taxonomy from the curated symptom-only ICD-11 export
# (data/only_medical_symptoms.csv), NOT the full WHO MMS export
# (data/icd11_mms_simplified.csv). The curated file is the one the offline
# embedding/indexing pipeline actually ran against -- state/upload_checkpoint.json
# records total=15471, matching only_medical_symptoms.csv's row count. Seeding
# from the full export would desync SQLite from the Upstash Vector index and
# pull in categories outside the current retrieval design.
db-seed-icd:
	uv run aegis-db seed --icd --csv-path ./data/only_medical_symptoms.csv

# Credential-free, reproducible end-to-end run of the clinical pipeline
# (submission -> AI reasoning -> human review -> decision -> cache
# projection) through the real FastAPI app with fake infra adapters.
# See scripts/demo_e2e.py.
demo:
	uv run python scripts/demo_e2e.py

# Production-readiness verification.
#
# Runs the same end-to-end workflow as `make demo`, but progressively replaces
# fake infrastructure adapters with their real implementations (Redis, Upstash
# Vector, embedding provider, LLM, PHI anonymizer, etc.).
#
# This verifies infrastructure integration without changing application logic.
integration:
	uv run python scripts/integration_e2e.py