{{
    config(
        materialized='view',
        description='AHRQ CLH database — healthcare infrastructure variables.'
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
                cast(null as varchar)  as county_year_key,
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
        lpad(cast(county_fips as varchar), 5, '0')      as county_fips,
        cast(year as integer)                           as year,
        cast(pct_uninsured_under65    as double)        as pct_uninsured_under65,
        cast(dist_trauma_center_miles as double)        as dist_trauma_center_miles,
        cast(mds_rate_per_100k        as double)        as mds_rate_per_100k,
        cast(rural_urban_code_2013    as integer)       as rural_urban_code_2013,

        -- Rural flag: RUCC 4–9 = non-metro (USDA classification)
        case
            when cast(rural_urban_code_2013 as integer) >= 4 then true
            when cast(rural_urban_code_2013 as integer) between 1 and 3 then false
        end                                             as is_rural

    from source
    where county_fips is not null
    and year::integer > 2016
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
