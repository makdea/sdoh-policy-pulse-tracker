# AHRQ SDOH Database — Manual Download Required

The AHRQ Social Determinants of Health (SDOH) database files must be downloaded manually
because the AHRQ website does not expose a public API.

## Download steps

1. Go to: https://www.ahrq.gov/sdoh/data-analytics/sdoh-data.html
2. Under "County-Level Data Files", download the Excel files for each available year.
3. Place them in **this directory** (`data/raw/ahrq/`).

Expected filenames:
```
SDOH_2016_COUNTY_1_0.xlsx
SDOH_2017_COUNTY_1_0.xlsx
SDOH_2018_COUNTY_1_0.xlsx
SDOH_2019_COUNTY_1_0.xlsx
SDOH_2020_COUNTY_1_0.xlsx
```

## What happens without these files

The pipeline degrades gracefully:
- The `stg_ahrq__sdoh` model returns an empty view.
- `int_county_annual_sdoh` LEFT JOINs AHRQ data, so all AHRQ columns are null.
- All mart models and the dashboard work normally; AHRQ-specific columns
  (`dist_trauma_center_miles`, `mds_per_10k`, `is_rural`) are simply null.

## Key variables extracted

| Variable | Description |
|---|---|
| `pct_uninsured_18_64` | % uninsured among adults 18–64 |
| `dist_trauma_center_miles` | Distance to nearest trauma center |
| `mds_per_10k` | Physicians per 10,000 population |
| `rural_urban_code` | USDA RUCC (1=most urban, 9=most rural) |
| `is_rural` | Boolean: RUCC ≥ 4 |
