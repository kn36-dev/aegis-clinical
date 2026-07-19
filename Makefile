.PHONY: dev-backend demo-server demo-local demo-local-all dev-frontend lint format test server-check demo

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

# Zero-external-dependency reviewer profile. Same FastAPI app, same
# LangGraph workflow, same routers as demo-server -- only AEGIS_PROFILE
# differs again, this time also swapping vector retrieval itself: the
# real ICD-11 taxonomy (from `make db-seed-icd`) is compiled into a
# local, file-backed vector index on first run (aegis.indexing.local_compiler)
# instead of querying Upstash Vector, so no Upstash Vector, OpenAI,
# Groq, or Redis credentials are needed at all -- not even a .env file.
# The first run compiles that local index (CPU-bound, several minutes
# over ~15k rows); every run after that loads the cached artifact
# instead. See docs/demo.md.
demo-local:
	AEGIS_PROFILE=demo-local uv run uvicorn aegis.api.main:app --app-dir src --reload --host 0.0.0.0 --port 9000

# Run the React frontend against the local FastAPI backend.
# VITE_API_BASE_URL defaults to the local development server but can be
# overridden by the caller, e.g.
# VITE_API_BASE_URL=https://staging.example.com make dev-frontend
dev-frontend:
	cd frontend && VITE_API_BASE_URL=$${VITE_API_BASE_URL:-http://localhost:9000} pnpm run dev
 
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

# Reproducible end-to-end run of the clinical pipeline (submission -> AI
# reasoning -> human review -> decision -> cache projection) through the
# real FastAPI app under AEGIS_PROFILE=demo: real embedding + real Upstash
# Vector retrieval, deterministic in-memory cache/reasoning/content
# adapters. Requires `make db-init && make db-seed-icd` to have been run
# first, and Upstash Vector + embedding credentials in .env. See
# scripts/demo_e2e.py and scripts/e2e_common.py.
demo:
	AEGIS_PROFILE=demo uv run python scripts/demo_e2e.py

# Infrastructure verification profile.
#
# Runs the same end-to-end workflow as `make demo`, but under
# AEGIS_PROFILE=integration: real Redis-backed cache and real CrewAI/Groq
# reasoning replace demo's in-memory adapters, so this exercises the full
# set of external infrastructure credentials (Upstash Vector, Upstash
# Redis, Groq) without changing application logic. Requires
# `make db-init && make db-seed-icd` first, plus the full credential set
# in .env. See scripts/integration_e2e.py and scripts/e2e_common.py.
integration:
	AEGIS_PROFILE=integration uv run python scripts/integration_e2e.py

# Redis cache-persistence verification.
#
# Companion to `make integration`, which must always exercise a cache
# MISS: this target submits the same logical note twice under a
# stable namespace to demonstrate the opposite -- cache MISS on the
# first submission, cache HIT (short-circuiting the graph) on the
# second. Requires the same prerequisites as `make integration`. See
# scripts/integration_cache_e2e.py.
integration-cache:
	AEGIS_PROFILE=integration uv run python scripts/integration_cache_e2e.py