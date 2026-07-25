{{
    config(
        materialized='view',
        description='BLS LAUS annual average county unemployment rates.'
    )
}}

with source as (
    select * from {{ source('raw', 'bls_laus') }}
),

cleaned as (
    select
        lpad(cast(county_fips as string), 5, '0')  as county_fips,
        lpad(cast(state_fips  as string), 2, '0')  as state_fips,
        cast(year as int64)                        as year,
        cast(unemployment_rate as float64)         as unemployment_rate

    from source
    where county_fips is not null
      and unemployment_rate is not null
      and cast(year as int64) between 2017 and 2024
      -- Drop state-level rows (county portion is '000')
      and right(lpad(cast(county_fips as string), 5, '0'), 3) != '000'
)

select
    {{ dbt_utils.generate_surrogate_key([
        'county_fips',
        'year'
    ]) }} as county_year_key,
    county_fips,
    state_fips,
    year,
    unemployment_rate
from cleaned
