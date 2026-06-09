"""
Ingest BLS Local Area Unemployment Statistics (LAUS) county data into DuckDB.

Uses bulk file download (la.data.64.County + la.series) rather than the BLS
API to avoid rate-limit issues across 3,000+ counties.

Bulk files: https://download.bls.gov/pub/time.series/la/
"""

import io
from pathlib import Path

import duckdb
import pandas as pd
import requests
from tqdm import tqdm

from .config import DB_PATH, RAW_DIR, BLS_YEARS

BLS_BASE = "https://download.bls.gov/pub/time.series/la"
DATA_FILE = "la.data.64.County"
SERIES_FILE = "la.series"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0"}

# Measure code 04 = unemployment rate (percent)
UNEMPLOYMENT_RATE_CODE = "03"

# M13 = annual average in BLS period codes
ANNUAL_PERIOD = "M13"


def _download_if_missing(filename: str, dest_dir: Path) -> Path:
    dest = dest_dir / filename
    if dest.exists():
        return dest
    url = f"{BLS_BASE}/{filename}"
    print(f"Downloading {url} …")
    with requests.get(url, headers=HEADERS, stream=True, timeout=300) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(dest, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc=filename
        ) as bar:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
                bar.update(len(chunk))
    return dest


def _parse_series(series_path: Path) -> pd.DataFrame:
    """Return mapping of series_id → state_fips, county_fips for unemployment rate."""
    series = pd.read_csv(
        series_path,
        sep="\t",
        engine="python",
        dtype=str,
    )
    print("CSV read.")
    series.columns = series.columns.str.strip()  # fix column names first
    series = series[["series_id", "area_type_code", "area_code", "measure_code"]]
    series["series_id"] = series["series_id"].str.strip()
    series["area_type_code"] = series["area_type_code"].str.strip()
    series["measure_code"] = series["measure_code"].str.strip()
    series["area_code"] = series["area_code"].str.strip()

    # County-level rows: area_type_code == 'F' (county and equivalent)
    county = series[
        (series["area_type_code"] == "F")
        & (series["measure_code"] == UNEMPLOYMENT_RATE_CODE)
    ].copy()

    # area_code format: 'CN' + state_fips(2) + county_fips(3) + padding
    county["state_fips"] = county["area_code"].str[2:4]
    county["county_fips"] = county["area_code"].str[4:7]
    county["county_fips_full"] = county["state_fips"] + county["county_fips"]

    return county[["series_id", "state_fips", "county_fips", "county_fips_full"]]


def ingest_bls_laus() -> None:
    raw_dir = Path(RAW_DIR) / "bls"
    raw_dir.mkdir(parents=True, exist_ok=True)

    series_path = _download_if_missing(SERIES_FILE, raw_dir)
    data_path = _download_if_missing(DATA_FILE, raw_dir)

    print("Parsing series definitions …")
    series_map = _parse_series(series_path)
    valid_ids = set(series_map["series_id"])

    print("Loading annual unemployment data …")
    chunks = []
    for chunk in pd.read_csv(
        data_path,
        sep=r"\t",
        engine="python",
        dtype=str,
        chunksize=200_000,
    ):
        chunk.columns = chunk.columns.str.strip()
        chunk["series_id"] = chunk["series_id"].str.strip()
        chunk["period"] = chunk["period"].str.strip()
        chunk["year"] = chunk["year"].str.strip()
        chunk["value"] = chunk["value"].str.strip()

        filtered = chunk[
            (chunk["series_id"].isin(valid_ids))
            & (chunk["period"] == ANNUAL_PERIOD)
            & (chunk["year"].astype(int).isin(BLS_YEARS))
        ]

        if not filtered.empty:
            chunks.append(filtered)

    data = pd.concat(chunks, ignore_index=True)
    data = data.merge(series_map, on="series_id", how="left")

    print("Data merged.")

    data["year"] = data["year"].astype(int)
    data["unemployment_rate"] = pd.to_numeric(data["value"], errors="coerce")
    data = data[data["unemployment_rate"].notna()]

    conn = duckdb.connect(DB_PATH)
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
    conn.execute("DROP TABLE IF EXISTS raw.bls_laus")
    conn.execute(
        """
        CREATE TABLE raw.bls_laus AS
        SELECT
            county_fips_full AS county_fips,
            state_fips,
            county_fips AS county_fips_within_state,
            year,
            unemployment_rate
        FROM data
        """
    )
    row_count = conn.execute("SELECT COUNT(*) FROM raw.bls_laus").fetchone()[0]
    conn.close()

    print(f"raw.bls_laus: {row_count:,} rows loaded")
