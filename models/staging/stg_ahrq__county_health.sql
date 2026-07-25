{{
    config(
        materialized='view',
        description='AHRQ CLH database — healthcare infrastructure variables.'
    )
}}

-- This model is a no-op view when no AHRQ data was ingested.
-- The intermediate layer performs a LEFT JOIN so missing AHRQ data
-- degrades gracefully rather than breaking the pipeline.
--
-- Existence check uses adapter.get_relation instead of a raw
-- information_schema query so it works across warehouses without needing
-- a project/dataset-qualified INFORMATION_SCHEMA reference.

{% set ahrq_source = source('raw', 'ahrq_clh') %}
{% set ahrq_relation = adapter.get_relation(
    database=ahrq_source.database,
    schema=ahrq_source.schema,
    identifier=ahrq_source.identifier
) if execute else none %}

with source as (
    {% if ahrq_relation is not none %}
        select * from {{ ahrq_source }}
    {% else %}
        -- AHRQ files not yet loaded; return empty scaffold matching the
        -- columns `cleaned` below expects.
        select
            cast(null as string)  as county_fips,
            cast(null as int64)   as year,
            cast(null as float64) as pct_uninsured_under65,
            cast(null as float64) as dist_trauma_center_miles,
            cast(null as float64) as mds_rate_per_100k,
            cast(null as int64)   as rural_urban_code_2013
        where 1 = 0
    {% endif %}
),

cleaned as (
    select
        lpad(cast(county_fips as string), 5, '0')       as county_fips,
        cast(year as int64)                             as year,
        cast(pct_uninsured_under65    as float64)       as pct_uninsured_under65,
        cast(dist_trauma_center_miles as float64)       as dist_trauma_center_miles,
        cast(mds_rate_per_100k        as float64)       as mds_rate_per_100k,
        cast(rural_urban_code_2013    as int64)         as rural_urban_code_2013,

        -- Rural flag: RUCC 4–9 = non-metro (USDA classification)
        case
            when cast(rural_urban_code_2013 as int64) >= 4 then true
            when cast(rural_urban_code_2013 as int64) between 1 and 3 then false
        end                                             as is_rural

    from source
    where county_fips is not null
    and cast(year as int64) > 2016
)

select
    {{ dbt_utils.generate_surrogate_key([
        'county_fips',
        'year'
    ]) }} as county_year_key,
    county_fips,
    year,
    pct_uninsured_under65,
    dist_trauma_center_miles,
    mds_rate_per_100k,
    rural_urban_code_2013,
    is_rural
from cleaned
