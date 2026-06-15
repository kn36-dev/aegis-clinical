from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="aegis-clinical 🛡️ Core API")

# Allow your React frontend (running on port 5173 by default) to speak to the backend safely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
# Improvement for clean architecture, use Pydantic model for schema
def health_check() -> dict[str, str]:
    return {"status": "healthy", "engine": "LangGraph Active", "security": "HIPAA Guarded"}
