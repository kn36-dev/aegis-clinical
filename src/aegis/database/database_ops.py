# src/aegis/cli/db_ops.py
import argparse
import logging
import sys
from pathlib import Path

# 1. Import the operational tools from your clean module
from aegis.database.database import (
    DEFAULT_CLINICAL_DB_PATH,
    DEFAULT_GRAPH_DB_PATH,
    init_clinical_database,
    init_graph_database,
)


def main():
    # 2. Since this is an entry-point CLI tool, it is allowed to configure logging
    logging.basicConfig(
        level=logging.INFO, format="⚙️  [CLI] %(asctime)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(description="Aegis Multi-Paradigm Micro-Scaffolder CLI")
    parser.add_argument(
        "--reset", action="store_true", help="Wipe and rebuild all schemas cleanly from scratch."
    )
    parser.add_argument("--clinical-path", type=str, default=str(DEFAULT_CLINICAL_DB_PATH))
    parser.add_argument("--graph-path", type=str, default=str(DEFAULT_GRAPH_DB_PATH))

    args = parser.parse_args()

    # 3. Add safety checks for high blast-radius commands (Principal Discipline!)
    if args.reset:
        confirm = input("⚠️ WARNING: You are about to wipe the database. Proceed? [y/N]: ")
        if confirm.lower() != "y":
            print("Operation aborted safely.")
            sys.exit(0)

    # 4. Invoke the library code
    init_clinical_database(db_path=Path(args.clinical_path), force_drop=args.reset)
    init_graph_database(db_path=Path(args.graph_path), force_drop=args.reset)


if __name__ == "__main__":
    main()
