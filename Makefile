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

db-init:
	uv run aegis-db init --all --reset

db-seed-icd:
	uv run aegis-db seed --icd --csv-path ./data/icd11_mms_simplified.csv

# Credential-free, reproducible end-to-end run of the clinical pipeline
# (submission -> AI reasoning -> human review -> decision -> cache
# projection) through the real FastAPI app with fake infra adapters.
# See scripts/demo_e2e.py.
demo:
	uv run python scripts/demo_e2e.py

integration:
	uv run python scripts/integration_e2e.py