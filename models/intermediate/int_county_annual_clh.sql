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
    select * from {{ ref('stg_sahie__uninsured') }}
),

bls as (
    select * from {{ ref('stg_bls__unemployment') }}
),

acs as (
    select * from {{ ref('stg_acs__poverty') }}
),

ahrq as (
    select * from {{ ref('stg_ahrq__clh') }}
),

state_lookup as (
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
        -- Geography
        s.county_fips,
        s.state_fips,
        s.county_name,
        sl.state_name,
        sl.state_abbr,
        sl.census_region,
        sl.census_division,

        -- Time
        s.year,

        -- SAHIE uninsurance
        s.pct_uninsured,
        s.n_uninsured,
        s.n_insured,
        s.pop_total_sahie,

        -- BLS unemployment
        b.unemployment_rate,

        -- ACS socioeconomic
        a.median_household_income,
        a.poverty_rate,
        a.pct_bachelors_plus,
        a.pct_hs_plus,
        a.pct_severe_rent_burden,

        -- AHRQ infrastructure (null when files not loaded)
        ah.dist_trauma_center_miles,
        ah.mds_per_10k,
        ah.rural_urban_code,
        ah.is_rural

    from sahie s
    left join bls  b  on s.county_fips = b.county_fips  and s.year = b.year
    left join acs  a  on s.county_fips = a.county_fips  and s.year = a.year
    left join ahrq ah on s.county_fips = ah.county_fips and s.year = ah.year
    left join state_lookup sl on s.state_fips = sl.state_fips
)

select * from joined
