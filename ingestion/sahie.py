"""
Ingest Census SAHIE (Small Area Health Insurance Estimates) into DuckDB.

SAHIE is the gold-standard source for county-level uninsurance rates.
Covers all 3,142 counties for 2016–2022 (latest available as of 2025).

API docs: https://www.census.gov/data/developers/data-sets/Health-Insurance-Statistics.html
"""

import requests
import pandas as pd
import duckdb
from tqdm import tqdm
from .config import DB_PATH, CENSUS_API_KEY, SAHIE_YEARS

BASE_URL = "https://api.census.gov/data/{year}/healthins/sahie"

# AGECAT=0 all ages, SEXCAT=0 both sexes, IPRCAT=0 all income levels
FIXED_PARAMS = {"AGECAT": "0", "SEXCAT": "0", "IPRCAT": "0"}


def _fetch_year(year: int) -> pd.DataFrame:
    params = {
        "get": "GEOID,NAME,PCTUI_PT,NUI_PT,NIC_PT",
        "for": "county:*",
        "in": "state:*",
        **FIXED_PARAMS,
    }
    if CENSUS_API_KEY:
        params["key"] = CENSUS_API_KEY

    resp = requests.get(BASE_URL.format(year=year), params=params, timeout=60)
    resp.raise_for_status()

    data = resp.json()
    df = pd.DataFrame(data[1:], columns=data[0])
    df["year"] = year
    return df


def ingest_sahie() -> None:
    frames = []
    for year in tqdm(SAHIE_YEARS, desc="SAHIE"):
        try:
            frames.append(_fetch_year(year))
        except Exception as exc:
            print(f"  WARNING: SAHIE {year} failed — {exc}")

    if not frames:
        raise RuntimeError("No SAHIE data fetched. Check CENSUS_API_KEY.")

    df = pd.concat(frames, ignore_index=True)

    # Normalize types
    df["PCTUI_PT"] = pd.to_numeric(df["PCTUI_PT"], errors="coerce")
    df["NUI_PT"] = pd.to_numeric(df["NUI_PT"], errors="coerce")
    df["NIC_PT"] = pd.to_numeric(df["NIC_PT"], errors="coerce")
    df["year"] = df["year"].astype(int)
    # GEOID from SAHIE is 5-char county FIPS
    df["GEOID"] = df["GEOID"].str.zfill(5)

    conn = duckdb.connect(DB_PATH)
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
    conn.execute("DROP TABLE IF EXISTS raw.sahie_uninsured")
    conn.execute("CREATE TABLE raw.sahie_uninsured AS SELECT * FROM df")
    row_count = conn.execute("SELECT COUNT(*) FROM raw.sahie_uninsured").fetchone()[0]
    conn.close()

    print(f"raw.sahie_uninsured: {row_count:,} rows loaded")
