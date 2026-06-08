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
        cast(year as integer)                               as year,

        -- Income
        nullif(cast(median_household_income as double), -666666666)
                                                            as median_household_income,

        -- Poverty
        cast(poverty_rate as double)                        as poverty_rate,
        cast(n_below_poverty as double)                     as n_below_poverty,
        cast(poverty_universe as double)                    as poverty_universe,

        -- Education
        cast(pct_bachelors_plus as double)                  as pct_bachelors_plus,
        cast(pct_hs_plus as double)                         as pct_hs_plus,

        -- Housing cost burden
        cast(pct_severe_rent_burden as double)              as pct_severe_rent_burden

    from source
    where county_fips is not null
      and cast(year as integer) between 2016 and 2022
      and right(county_fips, 3) != '000'
)

select * from cleaned
