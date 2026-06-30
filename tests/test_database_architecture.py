# from __future__ import annotations

# import csv
# import json
# from pathlib import Path
# from unittest.mock import Mock

# import pytest

# from aegis.database.adapters import UpstashRedisAdapter, UpstashVectorAdapter
# from aegis.database.cli import main
# from aegis.database.connection import get_db_connection
# from aegis.database.database import get_database_status, init_clinical_database, init_graph_database
# from aegis.database.repository import (
#     ClinicalMatchRecord,
#     ClinicalRegistryRepository,
#     Icd11TaxonomyRecord,
# )
# from aegis.database.seeds import seed_icd11


# def write_icd_csv(path: Path) -> None:
#     with path.open("w", encoding="utf-8", newline="") as handle:
#         writer = csv.writer(handle)
#         writer.writerow(["Code", "Title", "ClassKind"])
#         writer.writerow(["A00", "Cholera", "category"])
#         writer.writerow(["A00.1", "Cholera due to Vibrio cholerae", "category"])


# def write_mock_cases(path: Path) -> None:
#     payload = [
#         {
#             "patient_id": "patient-1",
#             "medical_record_number": "MRN-1",
#             "first_name": "Ada",
#             "last_name": "Lovelace",
#             "date_of_birth": "1815-12-10",
#             "case_id": "case-1",
#             "status": "pending_ai",
#             "ingress_timestamp": "2026-01-01T00:00:00Z",
#             "raw_clinical_note": "Patient reported fever.",
#             "anonymized_clinical_note": "Patient reported fever.",
#         }
#     ]
#     path.write_text(json.dumps(payload), encoding="utf-8")


# def test_migrations_are_ordered_and_idempotent(tmp_path: Path) -> None:
#     clinical_db = tmp_path / "clinical.db"
#     graph_db = tmp_path / "graph.db"

#     init_clinical_database(clinical_db)
#     init_clinical_database(clinical_db)
#     init_graph_database(graph_db)

#     assert clinical_db.exists()
#     assert graph_db.exists()

#     with get_db_connection(clinical_db) as conn:
#         tables = {
#             row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
#         }

#     assert "patient_identity_vault" in tables
#     assert "icd11_taxonomy_reference" in tables

#     migration_dir = Path(__file__).resolve().parents[1] / "src" / "aegis" / "database" / "migration"
#     prefixed_files = sorted(path.name for path in migration_dir.glob("0*.sql"))
#     assert len(prefixed_files) >= 8


# def test_seeders_are_idempotent_and_seed_taxonomy(tmp_path: Path) -> None:
#     clinical_db = tmp_path / "clinical.db"
#     csv_path = tmp_path / "taxonomy.csv"
#     write_icd_csv(csv_path)

#     init_clinical_database(clinical_db)
#     first_count = seed_icd11(db_path=clinical_db, csv_path=csv_path)
#     second_count = seed_icd11(db_path=clinical_db, csv_path=csv_path)

#     assert first_count == second_count == 2

#     with get_db_connection(clinical_db) as conn:
#         rows = conn.execute("SELECT code FROM icd11_taxonomy_reference ORDER BY code").fetchall()

#     assert [row[0] for row in rows] == ["A00", "A00.1"]


# def test_repository_upsert_select_and_rollback(tmp_path: Path) -> None:
#     database_path = tmp_path / "clinical.db"
#     init_clinical_database(database_path)
#     repository = ClinicalRegistryRepository(database_path)

#     record = ClinicalMatchRecord(
#         patient_id="patient-1",
#         raw_notes="some note",
#         clinical_notes_clear="some note",
#         icd11_codes=["A00"],
#         status="PENDING_ANONYMIZATION",
#         version=1,
#     )

#     repository.upsert_patient_case(record)
#     reloaded = repository.get_patient_case("patient-1")
#     assert reloaded is not None
#     assert reloaded.icd11_codes == ["A00"]

#     taxonomy = Icd11TaxonomyRecord(
#         code="A00", title="Cholera", class_kind="category", context_path="root"
#     )
#     repository.upsert_icd11_entry(taxonomy)
#     selected = repository.select_icd11_entry("A00")
#     assert selected is not None
#     assert selected.title == "Cholera"

#     with pytest.raises(RuntimeError):
#         with repository.transaction():
#             repository.upsert_patient_case(
#                 ClinicalMatchRecord(
#                     patient_id="patient-2", raw_notes="new", icd11_codes=[], version=1
#                 )
#             )
#             raise RuntimeError("boom")

#     assert repository.get_patient_case("patient-2") is None


# def test_sqlite_pragmas_and_concurrency_defaults(tmp_path: Path) -> None:
#     database_path = tmp_path / "pragma.db"

#     with get_db_connection(database_path) as conn:
#         assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
#         assert conn.execute("PRAGMA busy_timeout").fetchone()[0] >= 30000
#         assert conn.execute("PRAGMA synchronous").fetchone()[0] == 1
#         assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


# def test_adapters_are_mockable_offline() -> None:
#     redis_adapter = UpstashRedisAdapter(url="redis://localhost:6379")
#     vector_adapter = UpstashVectorAdapter(url="https://example.com")

#     redis_client = Mock()
#     vector_client = Mock()

#     redis_adapter._client = redis_client
#     vector_adapter._client = vector_client

#     redis_adapter.set("a", "b")
#     redis_adapter.get("a")
#     vector_adapter.upsert("doc", {"text": "hello"})
#     vector_adapter.query("hello", top_k=1)

#     redis_client.set.assert_called_once_with("a", "b")
#     redis_client.get.assert_called_once_with("a")
#     vector_client.upsert.assert_called_once_with("doc", {"text": "hello"})
#     vector_client.query.assert_called_once_with("hello", top_k=1)


# def test_cli_scaffold_seed_and_status(tmp_path: Path) -> None:
#     clinical_db = tmp_path / "clinical.db"
#     graph_db = tmp_path / "graph.db"
#     csv_path = tmp_path / "taxonomy.csv"
#     json_path = tmp_path / "cases.json"
#     write_icd_csv(csv_path)
#     write_mock_cases(json_path)

#     assert (
#         main(
#             [
#                 "scaffold",
#                 "--reset",
#                 "--clinical-path",
#                 str(clinical_db),
#                 "--graph-path",
#                 str(graph_db),
#             ]
#         )
#         == 0
#     )
#     assert main(["seed", "--icd", "--db-path", str(clinical_db), "--csv-path", str(csv_path)]) == 0
#     assert (
#         main(["seed", "--cases", "--db-path", str(clinical_db), "--json-path", str(json_path)]) == 0
#     )

#     status = get_database_status(clinical_db, graph_db)
#     assert status["clinical_exists"] is True
#     assert status["graph_exists"] is True
#     assert status["clinical_tables"]
