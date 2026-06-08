"""
Run all ingestion scripts in order.

Usage:
    python -m ingestion.run_all
    python -m ingestion.run_all --skip ahrq    # skip AHRQ (needs manual download)
"""

import argparse
import sys
import time

from .sahie import ingest_sahie
from .bls_laus import ingest_bls_laus
from .acs_poverty import ingest_acs_poverty
from .ahrq_clh import ingest_ahrq_clh


STEPS = [
    ("sahie", "Census SAHIE uninsurance estimates", ingest_sahie),
    ("bls", "BLS LAUS county unemployment", ingest_bls_laus),
    ("acs", "ACS 5-year poverty / income / education", ingest_acs_poverty),
    ("ahrq", "AHRQ SDOH infrastructure variables", ingest_ahrq_clh),
]


def main():
    parser = argparse.ArgumentParser(description="Ingest all SDOH data sources.")
    parser.add_argument(
        "--skip",
        nargs="*",
        default=[],
        help="Source keys to skip (sahie, bls, acs, ahrq)",
    )
    parser.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="Run only these source keys",
    )
    args = parser.parse_args()

    total_start = time.time()
    errors = []

    for key, label, fn in STEPS:
        if args.only is not None and key not in args.only:
            continue
        if key in args.skip:
            print(f"[SKIP] {label}")
            continue

        print(f"\n{'='*60}")
        print(f"[{key.upper()}] {label}")
        print("=" * 60)
        t0 = time.time()
        try:
            fn()
            print(f"  Done in {time.time() - t0:.1f}s")
        except Exception as exc:
            print(f"  ERROR: {exc}")
            errors.append((key, exc))

    elapsed = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"Ingestion complete in {elapsed:.1f}s")
    if errors:
        print(f"  {len(errors)} source(s) failed: {[k for k, _ in errors]}")
        print("  Run `dbt run` once at least SAHIE + BLS + ACS succeed.")
        sys.exit(1)
    else:
        print("  All sources loaded successfully.")
        print("  Next step: dbt seed && dbt run --profiles-dir .")


if __name__ == "__main__":
    main()
