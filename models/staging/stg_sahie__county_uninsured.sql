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
        -- SAHIE GEOID is the 5-digit county FIPS
        lpad(cast("GEOID" as varchar), 5, '0')              as county_fips,
        left(lpad(cast("GEOID" as varchar), 5, '0'), 2)     as state_fips,
        "NAME"                                               as county_name,
        cast(year as integer)                                as year,

        -- Core uninsurance metrics
        -- PCTUI_PT is suppressed (null) for small counties; preserve nulls.
        try_cast("PCTUI_PT" as double) / 100.0               as pct_uninsured,
        try_cast("NUI_PT"   as double)                       as n_uninsured,
        try_cast("NIC_PT"   as double)                       as n_insured,

        -- Derived total population from insured + uninsured
        try_cast("NUI_PT" as double)
            + try_cast("NIC_PT" as double)                   as pop_total_sahie

    from source
    where "GEOID" is not null
      and cast(year as integer) between 2016 and 2022
      -- Exclude state-level aggregate rows (FIPS ends in '000')
      and right(lpad(cast("GEOID" as varchar), 5, '0'), 3) != '000'
)

select * from cleaned
