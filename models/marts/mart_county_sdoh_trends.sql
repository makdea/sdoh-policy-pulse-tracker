{{
    config(
        materialized='table',
        description='Final wide table: one row per county per year, ready for dashboarding.'
    )
}}

-- This is the primary mart consumed by the choropleth and county drill-down
-- panels. Materialized as a table for dashboard query performance.

with base as (
    select * from {{ ref('int_medicaid_exposure') }}
),

final as (
    select
        -- Geography
        county_fips,
        state_fips,
        county_name,
        state_name,
        state_abbr,
        census_region,
        census_division,

        -- Time
        year,

        -- Era metadata
        era_name,
        president,
        era_color_hex,
        policy_event_label,

        -- Medicaid exposure
        expansion_status,
        expansion_year,
        is_expansion_state,
        years_since_expansion,
        expansion_phase,

        -- Core outcome: uninsurance
        pct_uninsured,
        n_uninsured,
        n_insured,
        sahie_total_population,

        -- Economic context
        unemployment_rate,
        median_household_income,
        poverty_rate,

        -- Educational attainment
        pct_bachelors_plus,
        pct_hs_plus,

        -- Housing
        pct_severe_rent_burden,

        -- Healthcare infrastructure (null without AHRQ files)
        dist_trauma_center_miles,
        mds_rate_per_100k,
        is_rural,
        rural_urban_code_2013,

        -- Composite disadvantage index: mean z-score across three key indicators.
        -- Null when any component is null. Higher value = more disadvantaged.
        (
            (pct_uninsured    - avg(pct_uninsured)    over ()) / nullif(stddev(pct_uninsured)    over (), 0)
          + (poverty_rate     - avg(poverty_rate)     over ()) / nullif(stddev(poverty_rate)     over (), 0)
          + (unemployment_rate - avg(unemployment_rate) over ()) / nullif(stddev(unemployment_rate) over (), 0)
        ) / 3.0                                              as sdoh_disadvantage_index

    from base
)

select
    county_fips,
    state_fips,
    county_name,
    state_name,
    state_abbr,
    census_region,
    census_division,
    year,
    era_name,
    president,
    era_color_hex,
    policy_event_label,
    expansion_status,
    expansion_year,
    is_expansion_state,
    years_since_expansion,
    expansion_phase,
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
    is_rural,
    rural_urban_code_2013,
    sdoh_disadvantage_index
from final
