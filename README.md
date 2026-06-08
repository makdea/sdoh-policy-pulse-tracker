# SDOH Policy Pulse Tracker

A dbt project that tracks how social determinants of health shifted across three political eras — **Trump 1 (2017–2020)**, **Biden (2021–2024)**, and **Trump 2 (2025–)** — using county-level public data ingested into DuckDB, modeled in dbt, and visualized in Plotly Dash.

---

## Architecture

```
Raw APIs / Files
      │
      ▼
ingestion/ (Python)
      │  writes raw.* tables
      ▼
DuckDB (data/sdoh_pulse.duckdb)
      │
      ▼
dbt models
  staging/      ← clean + type-cast raw tables (views)
  intermediate/ ← join sources into county × year spine (views)
  marts/        ← analytical tables for dashboarding (tables)
      │
      ▼
dashboard/app.py  (Plotly Dash)
```

---

## Data Sources

| Source | What it provides | Years | Access |
|---|---|---|---|
| [Census SAHIE](https://www.census.gov/data/developers/data-sets/Health-Insurance-Statistics.html) | County uninsurance rates | 2016–2022 | Free API key |
| [BLS LAUS](https://download.bls.gov/pub/time.series/la/) | County unemployment rates | 2016–2024 | Bulk download |
| [Census ACS 5-year](https://www.census.gov/data/developers/data-sets/acs-5year.html) | Poverty, income, education, housing | 2016–2022 | Free API key |
| [AHRQ SDOH](https://www.ahrq.gov/sdoh/data-analytics/sdoh-data.html) | Healthcare infrastructure, rurality | 2016–2020 | Manual download |
| Seeds | Medicaid expansion status (KFF), policy eras, state FIPS | Static | In repo |

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Git

### 2. Create and activate a virtual environment

```bash
# Create
python -m venv .venv

# Activate — macOS/Linux
source .venv/bin/activate

# Activate — Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Activate — Windows (cmd)
.venv\Scripts\activate.bat
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API keys

```bash
cp .env.example .env
# Edit .env — add your Census API key (free at https://api.census.gov/data/key_signup.html)
```

### 4. Initialize the database

```bash
python setup_db.py
```

### 5. Ingest data

```bash
# Ingest SAHIE + BLS + ACS (AHRQ requires manual download — see data/raw/ahrq/README.md)
python -m ingestion.run_all --skip ahrq

# Or ingest everything if you've downloaded AHRQ files:
python -m ingestion.run_all
```

### 6. Run the dbt pipeline

```bash
dbt deps                        # install packages
dbt seed --profiles-dir .       # load seed CSVs
dbt run --profiles-dir .        # build all models
dbt test --profiles-dir .       # run data quality tests
```

### 7. Launch the dashboard

```bash
python dashboard/app.py
# Open http://127.0.0.1:8050
```

Or use the Makefile shorthand: `make all`

---

## dbt Model Layers

### Staging (`models/staging/`)

One model per source. Responsibilities: cast types, standardize FIPS codes to 5-char strings, preserve nulls for suppressed values, filter to study years.

| Model | Source |
|---|---|
| `stg_sahie__uninsured` | Census SAHIE API |
| `stg_bls__unemployment` | BLS LAUS bulk files |
| `stg_acs__poverty` | Census ACS 5-year API |
| `stg_ahrq__sdoh` | AHRQ SDOH Excel files |

### Intermediate (`models/intermediate/`)

| Model | Purpose |
|---|---|
| `int_county_annual_sdoh` | Joins all staging models into a county × year spine |
| `int_policy_era_assignments` | Tags each row with era name + policy event labels |
| `int_medicaid_exposure` | Adds expansion status, expansion year, years since expansion, expansion phase |

### Marts (`models/marts/`)

| Model | Purpose |
|---|---|
| `mart_county_sdoh_trends` | Final wide table for choropleth + drill-down |
| `mart_era_comparisons` | Era × expansion-status aggregates for bar charts |
| `mart_diff_in_diff` | 2×2 DiD estimates across era transitions |

---

## Dashboard Panels

1. **Choropleth map** — county metric heatmap, slideable by year
2. **Era comparison bars** — avg outcomes by political era × Medicaid expansion status
3. **DiD chart** — difference-in-differences estimates (Trump1 → Biden) for 4 outcomes
4. **County drill-down** — click any county to see its full SDOH time series
5. **Correlation scatter** — unemployment vs uninsured rate, by era and expansion status

---

## Key Analytical Questions

- Did county-level uninsurance improve more in Medicaid expansion vs. non-expansion states under Biden vs. Trump 1?
- How did SNAP enrollment respond to unemployment shocks differently by era?
- Which counties saw the sharpest SDOH deterioration during Medicaid unwinding (2023–2024)?
- What is the estimated treatment effect of Medicaid expansion on uninsurance rates, controlling for era?

---

## Policy Event Annotations

The intermediate layer tags each year with documented federal policy changes:

| Year | Event |
|---|---|
| 2019 | ACA individual mandate penalty repealed |
| 2020 | COVID-19 continuous coverage requirement begins |
| 2021 | American Rescue Plan ACA subsidy expansion |
| 2023 | Medicaid unwinding begins (April) |
| 2024 | Medicaid unwinding ends (June); enrollment drops in 30 states |
| 2025 | Trump 2 Medicaid work requirements / DOGE cuts |

---

## Stack

| Layer | Tool |
|---|---|
| Storage | DuckDB (local, zero-setup) |
| Ingestion | Python (`requests`, `pandas`) |
| Transformation | dbt Core + dbt-duckdb |
| Testing | dbt generic tests + `dbt-expectations` |
| Visualization | Plotly Dash + Bootstrap |
