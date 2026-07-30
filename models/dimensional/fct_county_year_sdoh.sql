{{
    config(
        materialized='table',
        description='County-year fact table: raw numerators/denominators for self-serve ratio metrics.'
    )
}}

-- Grain: (county_fips, year). FKs to dim_county and dim_year.
-- Deliberately carries raw counts/numerators/denominators rather than
-- pre-computed rates wherever a source provides a count pair -- weighting
-- those into rates is Lightdash's job now (see project plan). Columns with
-- no natural numerator (median_household_income, dist_trauma_center_miles,
-- dist_obstetrics_miles, hpsa_primary_care) are kept as direct measures.

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

joined as (
    select
        sahie.county_fips,
        sahie.year,

        -- Uninsurance (SAHIE)
        sahie.n_uninsured,
        sahie.n_insured,
        sahie.sahie_total_population,

        -- Unemployment (BLS)
        bls.unemployment_level,
        bls.labor_force_level,

        -- Poverty (ACS)
        acs.n_below_poverty,
        acs.poverty_universe,

        -- Education (ACS)
        acs.edu_bachelors,
        acs.edu_hs_diploma,
        acs.edu_universe,

        -- Housing cost burden (ACS)
        acs.renters_severe_burden,
        acs.renters_total,

        -- Income (ACS) — no natural numerator/denominator pair
        acs.median_household_income,

        -- Healthcare infrastructure (AHRQ)
        ahrq.total_mds,
        ahrq.total_population,
        ahrq.dist_trauma_center_miles,
        ahrq.dist_obstetrics_miles,
        ahrq.hpsa_primary_care

    from sahie
    left join bls  on sahie.county_year_key = bls.county_year_key
    left join acs  on sahie.county_year_key = acs.county_year_key
    left join ahrq on sahie.county_year_key = ahrq.county_year_key
)

select
    {{ dbt_utils.generate_surrogate_key([
        'county_fips',
        'year'
    ]) }} as county_year_key,
    county_fips,
    year,
    n_uninsured,
    n_insured,
    sahie_total_population,
    unemployment_level,
    labor_force_level,
    n_below_poverty,
    poverty_universe,
    edu_bachelors,
    edu_hs_diploma,
    edu_universe,
    renters_severe_burden,
    renters_total,
    median_household_income,
    total_mds,
    total_population,
    dist_trauma_center_miles,
    dist_obstetrics_miles,
    hpsa_primary_care
from joined
