{{
    config(
        materialized='view',
        description='Spine: county × year with all SDOH sources joined.'
    )
}}

-- SAHIE is the authority for county × year coverage (2016–2022).
-- BLS extends through 2024 but we clip to SAHIE years for the core spine.
-- LEFT JOINs preserve all SAHIE rows even when other sources lack data.

with sahie as (
    select * from {{ ref('stg_sahie__county_uninsured') }}
),

bls as (
    select * from {{ ref('stg_bls__county_unemployment') }}
),

acs as (
    select * from {{ ref('stg_acs__county_poverty') }}
),

ahrq as (
    select * from {{ ref('stg_ahrq__county_health') }}
),

states as (
    select
        state_fips,
        state_name,
        state_abbr,
        census_region,
        census_division
    from {{ ref('state_fips_lookup') }}
),

joined as (
    select
        -- PK
        sahie.county_year_key,

        -- Geography
        sahie.county_fips,
        sahie.state_fips,
        sahie.county_name,
        states.state_name,
        states.state_abbr,
        states.census_region,
        states.census_division,

        -- Time
        sahie.year,

        -- SAHIE uninsurance
        sahie.pct_uninsured,
        sahie.n_uninsured,
        sahie.n_insured,
        sahie.sahie_total_population,

        -- BLS unemployment
        bls.unemployment_rate,

        -- ACS socioeconomic
        acs.median_household_income,
        acs.poverty_rate,
        acs.pct_bachelors_plus,
        acs.pct_hs_plus,
        acs.pct_severe_rent_burden,

        -- AHRQ infrastructure (null when files not loaded)
        ahrq.dist_trauma_center_miles,
        ahrq.mds_rate_per_100k,
        ahrq.rural_urban_code_2013,
        ahrq.is_rural

    from sahie
    left join bls  on sahie.county_year_key = bls.county_year_key
    left join acs  on sahie.county_year_key = acs.county_year_key
    left join ahrq on sahie.county_year_key = ahrq.county_year_key
    left join states on sahie.state_fips = states.state_fips
)

select
    county_year_key,
    county_fips,
    state_fips,
    county_name,
    state_name,
    state_abbr,
    census_region,
    census_division,
    year,
    pct_uninsured,
    n_uninsured,
    n_insured,
    sahie_total_population,
    unemployment_rate,
    median_household_income,
    poverty_rate,
    pct_bachelors_plus,
    pct_hs_plus,
    pct_severe_rent_burden,
    dist_trauma_center_miles,
    mds_rate_per_100k,
    rural_urban_code_2013,
    is_rural
from joined
