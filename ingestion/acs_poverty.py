"""
Ingest ACS 5-Year Estimates (poverty, income, education, housing) into DuckDB.

Uses the Census Data API for county-level ACS 5-year estimates.
Variables fetched:
  B19013_001E  median household income
  B17001_002E  population below poverty level
  B17001_001E  poverty universe (denominator)
  B15003_001E  educational attainment universe
  B15003_017E  high school diploma
  B15003_022E  bachelor's degree
  B25070_001E  renter universe
  B25070_010E  rent >= 50% of income (severely cost-burdened)

API docs: https://www.census.gov/data/developers/data-sets/acs-5year.html
"""

import requests
import pandas as pd
import duckdb
from tqdm import tqdm
from .config import DB_PATH, CENSUS_API_KEY, ACS_YEARS

BASE_URL = "https://api.census.gov/data/{year}/acs/acs5"

VARS = [
    "B19013_001E",  # median HH income
    "B17001_002E",  # below poverty
    "B17001_001E",  # poverty universe
    "B15003_001E",  # edu universe
    "B15003_017E",  # HS diploma
    "B15003_022E",  # bachelor's
    "B25070_001E",  # renter universe
    "B25070_010E",  # severely cost-burdened renters
]

RENAME = {
    "B19013_001E": "median_household_income",
    "B17001_002E": "n_below_poverty",
    "B17001_001E": "poverty_universe",
    "B15003_001E": "edu_universe",
    "B15003_017E": "edu_hs_diploma",
    "B15003_022E": "edu_bachelors",
    "B25070_001E": "renters_total",
    "B25070_010E": "renters_severe_burden",
}


def _fetch_year(year: int) -> pd.DataFrame:
    params = {
        "get": f"NAME,{','.join(VARS)}",
        "for": "county:*",
        "in": "state:*",
    }
    if CENSUS_API_KEY:
        params["key"] = CENSUS_API_KEY

    resp = requests.get(BASE_URL.format(year=year), params=params, timeout=90)
    resp.raise_for_status()

    data = resp.json()
    df = pd.DataFrame(data[1:], columns=data[0])
    df["year"] = year
    return df


def ingest_acs_poverty() -> None:
    frames = []
    for year in tqdm(ACS_YEARS, desc="ACS 5-year"):
        try:
            frames.append(_fetch_year(year))
        except Exception as exc:
            print(f"  WARNING: ACS {year} failed — {exc}")

    if not frames:
        raise RuntimeError("No ACS data fetched. Check CENSUS_API_KEY.")

    df = pd.concat(frames, ignore_index=True)
    df.rename(columns=RENAME, inplace=True)

    # Build 5-digit county FIPS
    df["county_fips"] = df["state"].str.zfill(2) + df["county"].str.zfill(3)
    df["state_fips"] = df["state"].str.zfill(2)
    df["year"] = df["year"].astype(int)

    # Coerce numerics (Census uses -666666666 for N/A)
    num_cols = list(RENAME.values())
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df.loc[df[col] < 0, col] = None

    # Derived rates
    df["poverty_rate"] = df["n_below_poverty"] / df["poverty_universe"]
    df["pct_bachelors_plus"] = (
        df["edu_bachelors"] / df["edu_universe"]
    )
    df["pct_hs_plus"] = (
        (df["edu_hs_diploma"] + df["edu_bachelors"]) / df["edu_universe"]
    )
    df["pct_severe_rent_burden"] = (
        df["renters_severe_burden"] / df["renters_total"]
    )

    conn = duckdb.connect(DB_PATH)
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
    conn.execute("DROP TABLE IF EXISTS raw.acs_poverty")
    conn.execute("CREATE TABLE raw.acs_poverty AS SELECT * FROM df")
    row_count = conn.execute("SELECT COUNT(*) FROM raw.acs_poverty").fetchone()[0]
    conn.close()

    print(f"raw.acs_poverty: {row_count:,} rows loaded")
