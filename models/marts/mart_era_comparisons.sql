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
        -- approx_quantiles(x, 2)[offset(1)] is BigQuery's equivalent of
        -- median() (no exact MEDIAN aggregate on BigQuery)
        approx_quantiles(pct_uninsured, 2)[offset(1)]               as median_pct_uninsured,
        stddev(pct_uninsured)                                       as sd_pct_uninsured,

        -- Raw sums for a properly population-weighted uninsurance rate
        -- (sum(n_uninsured)/sum(sahie_total_population)), instead of
        -- avg_pct_uninsured's mean-of-counties. Sums-of-sums still roll up
        -- correctly if Lightdash further aggregates across these cells.
        sum(n_uninsured)                                            as sum_n_uninsured,
        sum(sahie_total_population)                                 as sum_sahie_total_population,

        -- Unemployment
        avg(unemployment_rate)                                      as avg_unemployment_rate,
        approx_quantiles(unemployment_rate, 2)[offset(1)]           as median_unemployment_rate,

        -- Poverty
        avg(poverty_rate)                                           as avg_poverty_rate,
        approx_quantiles(poverty_rate, 2)[offset(1)]                as median_poverty_rate,

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

select
    era_name,
    president,
    era_color_hex,
    is_expansion_state,
    expansion_status,
    census_region,
    n_counties,
    n_county_years,
    avg_pct_uninsured,
    median_pct_uninsured,
    sd_pct_uninsured,
    sum_n_uninsured,
    sum_sahie_total_population,
    avg_unemployment_rate,
    median_unemployment_rate,
    avg_poverty_rate,
    median_poverty_rate,
    avg_median_hh_income,
    avg_pct_bachelors_plus,
    avg_pct_severe_rent_burden,
    era_start_year,
    era_end_year,
    era_sort_order
from with_order
order by era_sort_order, is_expansion_state desc
