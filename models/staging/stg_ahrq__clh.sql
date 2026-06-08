{{
    config(
        materialized='view',
        description='AHRQ SDOH database — healthcare infrastructure variables.'
    )
}}

-- This model is a no-op view when no AHRQ data was ingested.
-- The intermediate layer performs a LEFT JOIN so missing AHRQ data
-- degrades gracefully rather than breaking the pipeline.

{% set ahrq_exists %}
    select count(*) from information_schema.tables
    where table_schema = 'raw' and table_name = 'ahrq_clh'
{% endset %}

with source as (
    {% if execute %}
        {% set result = run_query(ahrq_exists) %}
        {% if result.columns[0].values()[0] > 0 %}
            select * from {{ source('raw', 'ahrq_clh') }}
        {% else %}
            -- AHRQ files not yet loaded; return empty scaffold
            select
                cast(null as varchar)  as county_fips,
                cast(null as integer)  as year,
                cast(null as double)   as pct_uninsured_18_64,
                cast(null as double)   as median_hh_income,
                cast(null as double)   as pct_below_poverty,
                cast(null as double)   as pct_unemployed,
                cast(null as double)   as dist_trauma_center_miles,
                cast(null as double)   as mds_per_10k,
                cast(null as integer)  as rural_urban_code
            where 1 = 0
        {% endif %}
    {% else %}
        select * from {{ source('raw', 'ahrq_clh') }}
    {% endif %}
),

cleaned as (
    select
        lpad(cast(county_fips as varchar), 5, '0')  as county_fips,
        cast(year as integer)                        as year,
        cast(pct_uninsured_18_64    as double)       as ahrq_pct_uninsured_18_64,
        cast(dist_trauma_center_miles as double)     as dist_trauma_center_miles,
        cast(mds_per_10k            as double)       as mds_per_10k,
        cast(rural_urban_code       as integer)      as rural_urban_code,

        -- Rural flag: RUCC 4–9 = non-metro (USDA classification)
        case
            when cast(rural_urban_code as integer) >= 4 then true
            when cast(rural_urban_code as integer) between 1 and 3 then false
        end                                          as is_rural

    from source
    where county_fips is not null
)

select * from cleaned
