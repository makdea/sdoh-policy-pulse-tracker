#!/usr/bin/env python3
"""Initialize the DuckDB database and directory structure."""
import os
from pathlib import Path
import duckdb


def setup():
    db_path = os.environ.get("DUCKDB_PATH", "data/sdoh_pulse.duckdb")

    for d in ["data/raw/bls", "data/raw/ahrq"]:
        Path(d).mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(db_path)
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
    conn.close()

    print(f"Database initialized at {db_path}")
    print("Place AHRQ SDOH Excel files in data/raw/ahrq/ before running ingestion.")
    print("See data/raw/ahrq/README.md for download instructions.")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    setup()
