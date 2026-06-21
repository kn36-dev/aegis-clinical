.PHONY: dev-backend dev-frontend lint format test

# Run the FastAPI server on our unexcluded port
dev-backend:
	uv run uvicorn aegis.api.main:app --app-dir src --reload --host 0.0.0.0 --port 9000

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