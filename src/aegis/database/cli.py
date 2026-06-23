"""Command-line utilities for initializing and seeding the Aegis databases.

Usage examples:
  python -m aegis.database.cli init --all --reset
  python -m aegis.database.cli seed --icd
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Sequence

from aegis.database.database import (
    init_all_databases,
    init_clinical_database,
    init_graph_database,
)
from aegis.database.seeds import seed_all, seed_icd11, seed_mock_cases


logger = logging.getLogger("aegis.database.cli")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aegis-db")
    subparsers = parser.add_subparsers(dest="command")

    p_init = subparsers.add_parser("init", help="Initialize database schema")
    p_init.add_argument("--reset", action="store_true", help="Drop and recreate databases")
    p_init.add_argument("--all", action="store_true", help="Init both clinical and graph dbs")
    p_init.add_argument("--clinical", action="store_true", help="Init clinical db")
    p_init.add_argument("--graph", action="store_true", help="Init graph db")
    p_init.add_argument("--clinical-path", type=str, help="Path to clinical DB file")
    p_init.add_argument("--graph-path", type=str, help="Path to graph DB file")

    p_seed = subparsers.add_parser("seed", help="Seed database with initial data")
    p_seed.add_argument("--icd", action="store_true", help="Seed ICD-11 taxonomy")
    p_seed.add_argument("--cases", action="store_true", help="Seed mock clinical cases")
    p_seed.add_argument("--all", action="store_true", help="Seed all available datasets")
    p_seed.add_argument("--db-path", type=str, help="Target clinical DB path for seeding")
    p_seed.add_argument("--csv-path", type=str, help="Path to ICD-11 CSV file")
    p_seed.add_argument("--json-path", type=str, help="Path to mock cases JSON")

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    if args.command == "init":
        clinical_path = Path(args.clinical_path) if args.clinical_path else None
        graph_path = Path(args.graph_path) if args.graph_path else None

        if args.all or (not args.clinical and not args.graph):
            init_all_databases(clinical_db=clinical_path, graph_db=graph_path, force_drop=args.reset)
        else:
            if args.clinical:
                init_clinical_database(db_path=clinical_path, force_drop=args.reset)
            if args.graph:
                init_graph_database(db_path=graph_path, force_drop=args.reset)

        return 0

    if args.command == "seed":
        db_path = Path(args.db_path) if args.db_path else None
        csv_path = Path(args.csv_path) if args.csv_path else None
        json_path = Path(args.json_path) if args.json_path else None

        if args.all or (not args.icd and not args.cases):
            results = seed_all(db_path=db_path)
            logger.info("Seeding complete: %s", results)
        else:
            if args.icd:
                count = seed_icd11(db_path=db_path, csv_path=csv_path)
                logger.info("ICD seed inserted %d records", count)
            if args.cases:
                count = seed_mock_cases(db_path=db_path, json_path=json_path)
                logger.info("Mock-cases seed inserted %d cases", count)

        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
