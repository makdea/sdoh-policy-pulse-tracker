{{
    config(
        materialized='view',
        description='ACS 5-year county-level poverty, income, education, and housing burden.'
    )
}}

with source as (
    select * from {{ source('raw', 'acs_poverty') }}
),

cleaned as (
    select
        county_fips,
        state_fips,
        cast(year as int64)                                 as year,

        -- Income
        nullif(cast(median_household_income as float64), -666666666)
                                                            as median_household_income,

        -- Poverty
        cast(poverty_rate as float64)                       as poverty_rate,
        cast(n_below_poverty as float64)                    as n_below_poverty,
        cast(poverty_universe as float64)                   as poverty_universe,

        -- Education
        cast(pct_bachelors_plus as float64)                 as pct_bachelors_plus,
        cast(pct_hs_plus as float64)                        as pct_hs_plus,

        -- Housing cost burden
        cast(pct_severe_rent_burden as float64)             as pct_severe_rent_burden

    from source
    where county_fips is not null
      and cast(year as int64) between 2017 and 2022
      and right(county_fips, 3) != '000'
)

select 
    {{ dbt_utils.generate_surrogate_key([
        'county_fips',
        'year'
    ]) }} as county_year_key,
    county_fips,
    state_fips,
    year,
    median_household_income,
    poverty_rate,
    n_below_poverty,
    poverty_universe,
    pct_bachelors_plus,
    pct_hs_plus,
    pct_severe_rent_burden
from cleaned
