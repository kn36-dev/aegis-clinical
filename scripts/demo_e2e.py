#!/usr/bin/env python3
"""
Runs the full AEGIS clinical pipeline end to end -- submission,
normalization, cache lookup, retrieval, AI reasoning, human review
interrupt, physician decision resume, persistence, and cache
projection -- through the real FastAPI HTTP boundary.

``TestClient`` wraps the real ``aegis.api.main.app``, including its real
lifespan, real LangGraph graph, and real SQLite-backed checkpointer; it
only skips opening an OS socket. Every collaborator that would
otherwise require a network credential (Upstash Vector, Upstash Redis,
Groq/CrewAI reasoning, ICD-11 taxonomy validation) is substituted with
a deterministic in-memory fake via ``build_container``'s injectable
parameters. No ``.env`` file or API key is required, and no file under
``data/`` is touched -- both SQLite databases live in a temporary
directory for the lifetime of this script.

Usage:
    uv run python scripts/demo_e2e.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from aegis.application.container import build_container  # noqa: E402
from aegis.database.database import init_clinical_database  # noqa: E402
from tests.application.fakes import (  # noqa: E402
    KNOWN_ICD_CODE,
    FakeClinicalDecisionCacheRepository,
    FakeContentRepository,
    FakeEmbeddingProvider,
    FakeICDCodeValidator,
    FakePHIAnonymizer,
    FakeReasoningProvider,
    FakeVectorQueryProvider,
)

SAMPLE_NOTE_TEXT = (
    "Patient presents with acute watery diarrhea and mild dehydration. "
    "No fever. No blood in stool. Onset 12 hours ago."
)


class _DemoSettings:
    GRAPH_CHECKPOINT_DB_PATH: str
    RETRIEVAL_TOP_K = 3
    RETRIEVAL_SIMILARITY_THRESHOLD = None

    def __init__(self, graph_checkpoint_db_path: str) -> None:
        self.GRAPH_CHECKPOINT_DB_PATH = graph_checkpoint_db_path


def _print_stage(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def _print_http(method: str, path: str, request_json: dict | None, response) -> None:
    print(f"--> {method} {path}")
    if request_json is not None:
        print(f"    request:  {json.dumps(request_json)}")
    print(f"<-- {response.status_code}")
    print(f"    response: {json.dumps(response.json(), indent=2, default=str)}")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        content_reference = f"content-store://clinical-notes/{uuid4()}"

        db_path = tmp_path / "clinical_registry.db"
        init_clinical_database(db_path)
        connection = sqlite3.connect(db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON;")

        container = build_container(
            connection,
            cache_repository=FakeClinicalDecisionCacheRepository(),
            embedding_provider=FakeEmbeddingProvider(),
            vector_query_provider=FakeVectorQueryProvider(),
            reasoning_provider=FakeReasoningProvider(),
            reasoning_model_name="fake-model",
            icd_code_validator=FakeICDCodeValidator(),
            phi_anonymizer=FakePHIAnonymizer(),
            content_repository=FakeContentRepository(
                content_by_reference={content_reference: SAMPLE_NOTE_TEXT}
            ),
        )
        settings = _DemoSettings(str(tmp_path / "graph_checkpoints.db"))

        import aegis.api.main as main_module

        main_module.get_settings = lambda: settings
        main_module.open_clinical_connection = lambda _settings: connection
        main_module.build_infrastructure = lambda _settings, _conn: container

        with TestClient(main_module.app) as client:
            _print_stage("STAGE 1 -- Submit clinical note (cache miss expected)")
            submit_payload = {
                "patient_id": str(uuid4()),
                "content_reference": content_reference,
            }
            submit_response = client.post("/api/v1/clinical-notes", json=submit_payload)
            _print_http("POST", "/api/v1/clinical-notes", submit_payload, submit_response)
            assert submit_response.status_code == 202
            workflow_id = submit_response.json()["workflow_id"]

            _print_stage("STAGE 2 -- Physician retrieves the pending review")
            review_response = client.get(f"/api/v1/reviews/{workflow_id}")
            _print_http("GET", f"/api/v1/reviews/{workflow_id}", None, review_response)
            assert review_response.status_code == 200

            _print_stage("STAGE 3 -- Physician submits a decision (resumes the workflow)")
            decision_payload = {"selected_icd_codes": [KNOWN_ICD_CODE]}
            decision_response = client.post(
                f"/api/v1/reviews/{workflow_id}/decision", json=decision_payload
            )
            _print_http(
                "POST",
                f"/api/v1/reviews/{workflow_id}/decision",
                decision_payload,
                decision_response,
            )
            assert decision_response.status_code == 200
            assert decision_response.json()["decision_id"] is not None

            _print_stage("DONE -- ClinicalDecision persisted and projected to cache")
            print(f"case_id={decision_response.json()['case_id']}")
            print(f"decision_id={decision_response.json()['decision_id']}")

        connection.close()


if __name__ == "__main__":
    main()
