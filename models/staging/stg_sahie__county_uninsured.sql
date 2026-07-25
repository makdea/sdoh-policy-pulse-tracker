{{
    config(
        materialized='view',
        description='Cleaned SAHIE county-level uninsurance estimates.'
    )
}}

with source as (
    select * from {{ source('raw', 'sahie_uninsured') }}
),

cleaned as (
    select
        -- SAHIE geoid is the 5-digit county FIPS
        lpad(cast(geoid as string), 5, '0')              as county_fips,
        left(lpad(cast(geoid as string), 5, '0'), 2)     as state_fips,
        name                                              as county_name,
        cast(year as int64)                               as year,

        -- Core uninsurance metrics
        -- pctui_pt is suppressed (null) for small counties; preserve nulls.
        safe_cast(pctui_pt as float64) / 100.0               as pct_uninsured,
        safe_cast(nui_pt   as float64)                       as n_uninsured,
        safe_cast(nic_pt   as float64)                       as n_insured,

        -- Derived total population from insured + uninsured
        safe_cast(nui_pt as float64)
            + safe_cast(nic_pt as float64)                   as sahie_total_population
    from source
    where geoid is not null
      and cast(year as int64) between 2017 and 2022
      -- Exclude state-level aggregate rows (FIPS ends in '000')
      and right(lpad(cast(geoid as string), 5, '0'), 3) != '000'
)

select
    {{ dbt_utils.generate_surrogate_key([
        'county_fips',
        'year'
    ]) }} as county_year_key,
    county_fips,
    state_fips,
    county_name,
    year,
    pct_uninsured,
    n_uninsured,
    n_insured,
    sahie_total_population
from cleaned
