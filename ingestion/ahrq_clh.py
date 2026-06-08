"""
Load AHRQ Community-Level Health (CLH) Database county Excel files into DuckDB.

Files must be manually downloaded from:
  https://www.ahrq.gov/sdoh/data-analytics/clh-data.html

Place them in data/raw/ahrq/ with names like:
  clh_2016_county_2_0.xlsx
  clh_2017_county_2_0.xlsx
  ...

The CLH Database spans 2009–2023 at the county level and draws from 47 data
sources across five domains: social context, economic context, education,
physical infrastructure, and healthcare context. This script extracts a
curated subset of variables available across most years.

Documentation: CLH-Data-Sources-Documentation-2025.pdf
"""

from pathlib import Path
import duckdb
import pandas as pd
from tqdm import tqdm
from .config import DB_PATH, RAW_DIR

AHRQ_DIR = Path(RAW_DIR) / "ahrq"

# Core variables to extract — names as they appear in CLH county Excel files.
# We try each alias in order and take the first match, which handles any
# minor name variation across file years.
#
# Key CLH identifier columns (per documentation):
#   COUNTYFIPS  — 5-digit state+county FIPS (renamed from FIPSCODE in v2)
#   YEAR        — data year
#
# Variable naming conventions by source prefix:
#   ACS_    American Community Survey
#   AHRF_   Area Health Resources Files
#   SAHIE_  Census Small Area Health Insurance Estimates
#   SAIPE_  Census Small Area Income and Poverty Estimates
#   POS_    Provider of Services file (CMS)
#   HIFLD_  Homeland Infrastructure Foundation-Level Data
VARIABLE_MAP = {
    "county_fips": ["COUNTYFIPS", "FIPSCODE"],          # FIPSCODE was the v1 name
    "year": ["YEAR"],
    # Uninsured: SAHIE is the preferred county-level source (ACS as fallback)
    "pct_uninsured_under65": ["SAHIE_PCT_UNINSURED64", "ACS_PCT_UNINSURED", "ACS_PCT_UNINSURED_BELOW64"],
    # Income
    "median_hh_income": ["ACS_MEDIAN_HH_INC"],
    # Poverty: SAIPE is the standard county-level poverty estimate
    "pct_below_poverty": ["SAIPE_PCT_POV"],
    # Unemployment
    "pct_unemployed": ["ACS_PCT_UNEMPLOY"],
    # Education
    "pct_hs_graduate": ["ACS_PCT_HS_GRADUATE"],
    "pct_bachelors": ["ACS_PCT_BACHELOR_DGR"],
    # Population (weighted total, used as the CLH standard denominator)
    "total_population": ["ACS_TOT_POP_WT"],
    # Healthcare access — nearest trauma center (POS file, county-level)
    "dist_trauma_center_miles": ["POS_MEDIAN_DIST_TRAUMA"],
    # Physicians: rate per 100k (AHRF_MDS_RATE) and raw count (AHRF_TOT_MDS)
    "mds_rate_per_100k": ["AHRF_MDS_RATE"],
    "total_mds": ["AHRF_TOT_MDS"],
    # Rural-urban classification (2013 and 2023 vintages both included in CLH)
    "rural_urban_code_2013": ["AHRF_USDA_RUCC_2013"],
    "rural_urban_code_2023": ["AHRF_USDA_RUCC_2023"],
}


def _resolve_col(df: pd.DataFrame, aliases: list[str]) -> pd.Series | None:
    for alias in aliases:
        if alias in df.columns:
            return df[alias]
    return None


def _load_file(path: Path) -> pd.DataFrame | None:
    print(f"  Loading {path.name} …")
    try:
        raw = pd.read_excel(path, sheet_name="Data", dtype=str, engine="openpyxl")
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

    if df.empty:
        print(f"  WARNING: No recognized columns found in {path.name}")
        return None

    # COUNTYFIPS is 5 digits; CLH already stores it that way, but zfill
    # guards against any files where leading zeros were dropped on export.
    if "county_fips" in df.columns:
        df["county_fips"] = df["county_fips"].astype(str).str.strip().str.zfill(5)

    # Coerce numeric columns
    numeric_cols = [
        "pct_uninsured_under65", "median_hh_income", "pct_below_poverty",
        "pct_unemployed", "pct_hs_graduate", "pct_bachelors",
        "total_population", "dist_trauma_center_miles",
        "mds_rate_per_100k", "total_mds",
        "rural_urban_code_2013", "rural_urban_code_2023",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

    return df


def ingest_ahrq_clh() -> None:
    # CLH county files follow the pattern CLH_<YYYY>_COUNTY*.xlsx
    xlsx_files = sorted(AHRQ_DIR.glob("clh_*_county*.xlsx"))

    if not xlsx_files:
        print(
            "WARNING: No AHRQ CLH county XLSX files found in data/raw/ahrq/.\n"
            "  Download them from https://www.ahrq.gov/sdoh/data-analytics/sdoh-data.html\n"
            "  Expected filenames: CLH_<YYYY>_COUNTY*.csv (2009–2023)\n"
            "  Skipping CLH ingestion."
        )
        return

    frames = []
    for f in tqdm(xlsx_files, desc="AHRQ CLH"):
        df = _load_file(f)
        if df is not None and not df.empty:
            frames.append(df)

    if not frames:
        print("WARNING: No usable AHRQ CLH data loaded.")
        return

    combined = pd.concat(frames, ignore_index=True)

    conn = duckdb.connect(DB_PATH)
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
    conn.execute("DROP TABLE IF EXISTS raw.ahrq_clh")
    conn.execute("CREATE TABLE raw.ahrq_clh AS SELECT * FROM combined")
    row_count = conn.execute("SELECT COUNT(*) FROM raw.ahrq_clh").fetchone()[0]
    conn.close()

    print(f"raw.ahrq_clh: {row_count:,} rows loaded")
