"""
Load AHRQ SDOH database Excel files into DuckDB.

Files must be manually downloaded from:
  https://www.ahrq.gov/sdoh/data-analytics/sdoh-data.html

Place them in data/raw/ahrq/ with names like:
  SDOH_2016_COUNTY_1_0.xlsx
  SDOH_2017_COUNTY_1_0.xlsx
  ...

The AHRQ SDOH database spans five domains: social context, economic context,
education, physical infrastructure, and healthcare context. This script
extracts a curated subset of variables available across most years.
"""

from pathlib import Path
import duckdb
import pandas as pd
from tqdm import tqdm
from .config import DB_PATH, RAW_DIR

AHRQ_DIR = Path(RAW_DIR) / "ahrq"

# Core variables to extract — names stable across 2016–2020 files
# We try each alias and take the first match.
VARIABLE_MAP = {
    "county_fips": ["COUNTYFIPS", "FIPS", "countyfips"],
    "year": ["YEAR", "year"],
    "state_fips": ["STATEFIPS", "STATE_FIPS", "statefips"],
    "pct_uninsured_18_64": ["ACS_PCT_UNINSUR", "ACS_PCT_UNINSUR_18_64"],
    "median_hh_income": ["ACS_MEDIAN_HH_INC", "ACS_MED_HH_INC"],
    "pct_below_poverty": ["ACS_PCT_POV", "ACS_PCT_BELOW_POV"],
    "pct_unemployed": ["ACS_PCT_UNEMPLOYED", "ACS_PCT_UNEMPLOY"],
    "pct_no_hs_diploma": ["ACS_PCT_LESS_HS", "ACS_PCT_NO_HS"],
    "pct_bachelors": ["ACS_PCT_BACH_DGR", "ACS_PCT_BACHELOR"],
    "total_population": ["ACS_TOT_POP_US_ABOVE1", "ACS_TOT_POP", "TOTAL_POP"],
    "dist_trauma_center_miles": ["HIFLD_DIST_ATC", "DIST_ATC"],
    "mds_per_10k": ["AHRF_NUMMD", "NUM_MD_10K"],
    "rural_urban_code": ["RUCC_2013", "RUCC2013", "RURAL_URBAN_CODE"],
}


def _resolve_col(df: pd.DataFrame, aliases: list[str]) -> pd.Series | None:
    for alias in aliases:
        if alias in df.columns:
            return df[alias]
    return None


def _load_file(path: Path) -> pd.DataFrame | None:
    print(f"  Loading {path.name} …")
    try:
        raw = pd.read_excel(path, dtype=str, engine="openpyxl")
    except Exception as exc:
        print(f"  WARNING: Could not read {path.name} — {exc}")
        return None

    raw.columns = raw.columns.str.strip()

    result = {}
    for target_col, aliases in VARIABLE_MAP.items():
        series = _resolve_col(raw, aliases)
        if series is not None:
            result[target_col] = series.values
        else:
            result[target_col] = None

    df = pd.DataFrame({k: v for k, v in result.items() if v is not None})

    # Ensure county_fips is 5-char
    if "county_fips" in df.columns:
        df["county_fips"] = df["county_fips"].astype(str).str.zfill(5)

    # Coerce numerics
    numeric_cols = [
        "pct_uninsured_18_64", "median_hh_income", "pct_below_poverty",
        "pct_unemployed", "pct_no_hs_diploma", "pct_bachelors",
        "total_population", "dist_trauma_center_miles", "mds_per_10k",
        "rural_urban_code",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

    return df


def ingest_ahrq_sdoh() -> None:
    xlsx_files = sorted(AHRQ_DIR.glob("SDOH_*_COUNTY_*.xlsx"))

    if not xlsx_files:
        print(
            "WARNING: No AHRQ SDOH Excel files found in data/raw/ahrq/.\n"
            "  Download them from https://www.ahrq.gov/sdoh/data-analytics/sdoh-data.html\n"
            "  and retry. Skipping AHRQ ingestion."
        )
        return

    frames = []
    for f in tqdm(xlsx_files, desc="AHRQ SDOH"):
        df = _load_file(f)
        if df is not None and not df.empty:
            frames.append(df)

    if not frames:
        print("WARNING: No usable AHRQ data loaded.")
        return

    combined = pd.concat(frames, ignore_index=True)

    conn = duckdb.connect(DB_PATH)
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
    conn.execute("DROP TABLE IF EXISTS raw.ahrq_sdoh")
    conn.execute("CREATE TABLE raw.ahrq_sdoh AS SELECT * FROM combined")
    row_count = conn.execute("SELECT COUNT(*) FROM raw.ahrq_sdoh").fetchone()[0]
    conn.close()

    print(f"raw.ahrq_sdoh: {row_count:,} rows loaded")
