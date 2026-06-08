{{
    config(
        materialized='table',
        description='Era × expansion-status aggregates for bar chart comparison.'
    )
}}

-- Answers: did outcomes improve more in expansion states under Biden vs Trump1?
-- Groups: era × is_expansion_state (2 × 3 = 6 cells for each outcome).

with base as (
    select * from {{ ref('int_medicaid_exposure') }}
    where era_name is not null
),

aggregated as (
    select
        era_name,
        president,
        era_color_hex,
        is_expansion_state,
        expansion_status,
        census_region,

        -- Sample size
        count(distinct county_fips)                                 as n_counties,
        count(*)                                                    as n_county_years,

        -- Uninsurance
        avg(pct_uninsured)                                          as avg_pct_uninsured,
        median(pct_uninsured)                                       as median_pct_uninsured,
        stddev(pct_uninsured)                                       as sd_pct_uninsured,

        -- Unemployment
        avg(unemployment_rate)                                      as avg_unemployment_rate,
        median(unemployment_rate)                                   as median_unemployment_rate,

        -- Poverty
        avg(poverty_rate)                                           as avg_poverty_rate,
        median(poverty_rate)                                        as median_poverty_rate,

        -- Income
        avg(median_household_income)                                as avg_median_hh_income,

        -- Education
        avg(pct_bachelors_plus)                                     as avg_pct_bachelors_plus,

        -- Housing
        avg(pct_severe_rent_burden)                                 as avg_pct_severe_rent_burden,

        -- Era time range for display
        min(year)                                                   as era_start_year,
        max(year)                                                   as era_end_year

    from base
    group by
        era_name, president, era_color_hex,
        is_expansion_state, expansion_status,
        census_region
),

-- Add era ordering for consistent chart sort
with_order as (
    select
        *,
        case era_name
            when 'Trump1' then 1
            when 'Biden'  then 2
            when 'Trump2' then 3
        end as era_sort_order
    from aggregated
)

select * from with_order
order by era_sort_order, is_expansion_state desc
