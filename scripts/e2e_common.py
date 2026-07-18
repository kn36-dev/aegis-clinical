"""
Shared implementation for scripts/demo_e2e.py and scripts/integration_e2e.py.

Both scripts run the identical end-to-end clinical pipeline -- submission,
normalization, cache lookup, retrieval, AI reasoning, human review
interrupt, physician decision resume, persistence, and cache projection
-- through the real FastAPI HTTP boundary. The only thing that
distinguishes them is which collaborators ``AEGIS_PROFILE`` selects
(``aegis.api.bootstrap.build_infrastructure``); neither script constructs
an adapter itself, so that selection lives in exactly one place. This
module exists so that shared logic is not duplicated between the two
thin entry-point scripts.

``TestClient`` wraps the real ``aegis.api.main.app``, including its real
lifespan, real LangGraph graph, and real SQLite-backed checkpointer; it
only skips opening an OS socket. ``AppSettings``, ``open_clinical_connection``,
and ``build_infrastructure`` are the same composition root the FastAPI
app itself uses (``api/main.py``'s lifespan) -- this script does not
construct a second one.

Every profile this script can run under (``demo``, ``integration``) uses
real embedding and real Upstash Vector retrieval, so ``settings.CLINICAL_DB_PATH``
must already contain the seeded ICD-11 taxonomy the real Upstash Vector
index was built against -- run ``make db-init`` and ``make db-seed-icd``
first. This script does not seed the taxonomy itself and does not touch
a temporary/ephemeral database, since a fresh empty taxonomy would make
every real retrieval candidate fail ``ICDCodeValidator``.

The submitted note deliberately reuses one of ``aegis.api.bootstrap
.DEMO_SAMPLE_NOTES``'s fixed ``content_reference`` values rather than a
freshly-minted one -- see that constant's docstring and
``docs/tradeoffs_and_limitations.md``'s "Live-Credential Content Seeding
Gap" for why a fresh content_reference cannot resolve against the real
content store in any profile.

The physician's decision is read back from whatever the AI actually
recommended (``recommended_icd_codes`` on the review response) rather
than a hardcoded ICD code: real retrieval returns whatever the real
Upstash Vector index considers the closest match to this note's
embedding, which is not fixed across index/model changes.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from aegis.api.bootstrap import DEMO_SAMPLE_NOTES, build_infrastructure  # noqa: E402
from aegis.config import AppSettings  # noqa: E402
from aegis.database.database import init_clinical_database  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import Iterator

    from aegis.application.container import AegisContainer

_CONTENT_REFERENCE = next(iter(DEMO_SAMPLE_NOTES))


@dataclass(frozen=True)
class WorkflowSubmissionResult:
    """
    Outcome of one ``submit_and_resolve`` call.

    ``cache_hit`` distinguishes the two terminal shapes
    ``_invoke_workflow`` (``aegis.api.routers.clinical``) can return for
    a submission: ``True`` when the submit response already carried
    ``status=="completed"`` (``cache_lookup`` short-circuited the graph
    -- see ``_route_after_cache_lookup``), ``False`` when it suspended
    at ``human_review_pending`` and was walked through the full
    retrieval/reasoning/review/decision path below.
    """

    case_id: str
    decision_id: str
    cache_hit: bool


def _print_stage(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def _print_http(method: str, path: str, request_json: dict | None, response) -> None:
    print(f"--> {method} {path}")
    if request_json is not None:
        print(f"    request:  {json.dumps(request_json)}")
    print(f"<-- {response.status_code}")
    print(f"    response: {json.dumps(response.json(), indent=2, default=str)}")


def _require_seeded_taxonomy(connection) -> None:
    """
    Fail fast, with an actionable message, rather than deep inside the
    LangGraph retrieval node, when the local ICD-11 taxonomy table is
    empty -- see this module's docstring for why real retrieval requires
    it to already be seeded.
    """
    (count,) = connection.execute("SELECT COUNT(*) FROM icd11_taxonomy;").fetchone()
    if count == 0:
        raise SystemExit(
            "icd11_taxonomy is empty in the configured CLINICAL_DB_PATH. "
            "Run `make db-init && make db-seed-icd` before running this script."
        )


def _seed_patient_identity(connection, patient_id: str) -> None:
    connection.execute(
        """
        INSERT INTO patient_identity_vault (
            patient_id,
            medical_record_number,
            first_name,
            last_name,
            date_of_birth
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            patient_id,
            f"MRN-{uuid4()}",
            "Demo",
            "Patient",
            "1990-01-01",
        ),
    )
    connection.commit()


def open_e2e_connection(settings: AppSettings) -> sqlite3.Connection:
    """
    Open a SQLite connection for TestClient-based E2E execution.

    Unlike the production lifespan connection, this permits cross-thread
    usage because Starlette TestClient executes the ASGI lifespan and
    request handling across different threads.

    This keeps the production SQLite safety default unchanged while making
    the local E2E harness compatible with the testing runtime.
    """
    init_clinical_database(settings.CLINICAL_DB_PATH)

    connection = sqlite3.connect(
        settings.CLINICAL_DB_PATH,
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL;")
    connection.execute("PRAGMA busy_timeout=30000;")
    connection.execute("PRAGMA synchronous=NORMAL;")
    connection.execute("PRAGMA foreign_keys=ON;")

    return connection


def build_e2e_settings(namespace: str | None = None) -> AppSettings:
    """
    Build the ``AppSettings`` this E2E harness runs the app under.

    Under ``AEGIS_PROFILE=integration``, the Redis cache namespace is
    execution-scoped by default -- a fresh ``integration-<uuid4()>`` per
    process -- so a workflow-correctness run always starts from a cache
    MISS without ever deleting or clearing Redis (see
    ``integration_e2e.py``). Passing ``namespace`` overrides that
    default with a caller-chosen, stable namespace instead (see
    ``integration_cache_e2e.py``, which deliberately reuses one
    namespace across two submissions to exercise the cache-HIT path).
    """
    settings = AppSettings()

    if settings.AEGIS_PROFILE == "integration":
        return settings.model_copy(
            update={
                "REDIS_CACHE_NAMESPACE": namespace or f"integration-{uuid4()}",
            }
        )

    return settings


@contextmanager
def e2e_test_client(
    settings: AppSettings, connection: sqlite3.Connection
) -> Iterator[tuple[TestClient, AegisContainer]]:
    """
    Build the real ``AegisContainer`` for ``settings`` and yield a
    ``TestClient`` wrapping the real FastAPI app against it, alongside
    that same container.

    Patches ``aegis.api.main``'s composition-root hooks to return this
    exact ``connection``/``container`` rather than constructing a
    second one during the app's lifespan -- see this module's docstring
    for why the app must reuse them. The container is yielded too so a
    caller can reach real application services directly (e.g.
    ``integration_cache_e2e.py`` uses ``container.normalization_service``
    to compute a cache key) without constructing a second container.
    """
    container = build_infrastructure(settings, connection)

    import aegis.api.main as main_module

    main_module.get_settings = lambda: settings
    main_module.open_clinical_connection = lambda _settings: connection
    main_module.build_infrastructure = lambda _settings, _conn: container

    with TestClient(main_module.app) as client:
        yield client, container


def submit_and_resolve(
    client: TestClient,
    connection: sqlite3.Connection,
    content_reference: str = _CONTENT_REFERENCE,
) -> WorkflowSubmissionResult:
    """
    Submit one clinical note through the real HTTP boundary and drive
    it to completion.

    A cache MISS suspends the graph at the ``human_review_pending``
    interrupt, so this walks stage 2 (GET the pending review) and stage
    3 (POST the physician's decision) to resume it, exactly as the
    original single-shot script did. A cache HIT instead returns
    ``status=="completed"`` directly from the submit response (see
    ``aegis.api.routers.clinical._invoke_workflow``), so there is no
    review to walk -- this returns immediately in that case.
    """
    _print_stage("STAGE 1 -- Submit clinical note")
    patient_id = str(uuid4())
    _seed_patient_identity(connection, patient_id)

    submit_payload = {
        "patient_id": patient_id,
        "content_reference": content_reference,
    }
    submit_response = client.post("/api/v1/clinical-notes", json=submit_payload)
    _print_http("POST", "/api/v1/clinical-notes", submit_payload, submit_response)
    assert submit_response.status_code in (201, 202)
    submit_body = submit_response.json()
    workflow_id = submit_body["workflow_id"]

    if submit_body["status"] == "completed":
        _print_stage("DONE -- cache HIT, workflow completed without human review")
        return WorkflowSubmissionResult(
            case_id=submit_body["case_id"],
            decision_id=submit_body["decision_id"],
            cache_hit=True,
        )

    _print_stage("STAGE 2 -- Physician retrieves the pending review")
    review_response = client.get(f"/api/v1/reviews/{workflow_id}")
    _print_http("GET", f"/api/v1/reviews/{workflow_id}", None, review_response)
    assert review_response.status_code == 200
    recommended_icd_codes = [
        recommendation["icd_code"]
        for recommendation in review_response.json()["recommended_icd_codes"]
    ]

    _print_stage("STAGE 3 -- Physician submits a decision (resumes the workflow)")
    decision_payload = {"selected_icd_codes": recommended_icd_codes}
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
    decision_body = decision_response.json()
    assert decision_body["decision_id"] is not None

    _print_stage("DONE -- ClinicalDecision persisted and projected to cache")
    return WorkflowSubmissionResult(
        case_id=decision_body["case_id"],
        decision_id=decision_body["decision_id"],
        cache_hit=False,
    )


def main() -> None:
    settings = build_e2e_settings()

    connection = open_e2e_connection(settings)
    _require_seeded_taxonomy(connection)

    with e2e_test_client(settings, connection) as (client, _container):
        print(f"AEGIS_PROFILE={settings.AEGIS_PROFILE}")
        result = submit_and_resolve(client, connection)
        print(f"case_id={result.case_id}")
        print(f"decision_id={result.decision_id}")

    connection.close()
