#!/usr/bin/env python3
"""Lightweight entrypoint to run the database CLI without installing the package.

Usage from repo root:
  ./scaffold_db.py init --all --reset
  ./scaffold_db.py seed --icd
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
# Ensure `src` is on sys.path for editable/src-layout imports
sys.path.insert(0, str(ROOT / "src"))

from aegis.database.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
