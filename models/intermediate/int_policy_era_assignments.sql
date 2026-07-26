{{
    config(
        materialized='view',
        description='Assigns each county-year row to a political era (Trump1/Biden/Trump2).'
    )
}}

-- Policy eras are defined by calendar year in the seeds/policy_eras.csv seed.
-- Years at the boundary (2017, 2021, 2025) belong entirely to the new era
-- since the new administration takes office in January.

with spine as (
    select * from {{ ref('int_county_annual_clh') }}
),

eras as (
    select
        era_name,
        president,
        start_year,
        end_year,
        color_hex
    from {{ ref('policy_eras') }}
),

-- Annotate key policy events as year-flags for downstream annotation
policy_events as (
    select
        year,
        case
            when year = 2019 then 'ACA individual mandate penalty repealed'
            when year = 2020 then 'COVID-19: continuous coverage requirement (Mar)'
            when year = 2021 then 'American Rescue Plan ACA subsidy expansion'
            when year = 2023 then 'Medicaid unwinding begins (Apr)'
            when year = 2024 then 'Medicaid unwinding ends (Jun); enrollment drops'
            when year = 2025 then 'Trump2 Medicaid work requirements / DOGE cuts'
        end as policy_event_label
    from unnest([2016,2017,2018,2019,2020,2021,2022,2023,2024,2025]) as year
),

assigned as (
    select
        spine.*,
        eras.era_name,
        eras.president,
        eras.color_hex as era_color_hex,
        pol.policy_event_label

    from spine
    left join eras
        on spine.year between eras.start_year and eras.end_year
    left join policy_events pol
        on spine.year = pol.year
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
    is_rural,
    era_name,
    president,
    era_color_hex,
    policy_event_label
from assigned
