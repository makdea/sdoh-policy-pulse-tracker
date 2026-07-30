{{
    config(
        materialized='table',
        description='County dimension: geography + Medicaid-expansion context, flattened to one join.'
    )
}}

-- Grain: county_fips. Built from stg_sahie__county_uninsured (the
-- authoritative county × year spine's geography) plus the state_fips_lookup
-- and medicaid_expansion_status seeds. Flattened rather than snowflaked so a
-- Lightdash user never needs more than one join to get geography +
-- expansion context, mirroring the join logic previously in
-- int_county_annual_clh.sql / int_medicaid_exposure.sql.

with counties as (
    select distinct
        county_fips,
        state_fips,
        county_name
    from {{ ref('stg_sahie__county_uninsured') }}
),

ahrq as (
    select distinct
        county_fips,
        rural_urban_code_2013,
        is_rural
    from {{ ref('stg_ahrq__county_health') }}
    qualify row_number() over (
        partition by county_fips
        order by year desc
    ) = 1
),

states as (
    select
        state_fips,
        state_name,
        state_abbr,
        census_region,
        census_division
    from {{ ref('state_fips_lookup') }}
),

expansion as (
    select
        state_fips,
        expansion_status,
        safe_cast(expansion_year as int64) as expansion_year,
        case when expansion_status = 'expanded' then true else false end as is_expansion_state
    from {{ ref('medicaid_expansion_status') }}
),

joined as (
    select
        counties.county_fips,
        counties.county_name,
        counties.state_fips,
        states.state_name,
        states.state_abbr,
        states.census_region,
        states.census_division,
        expansion.expansion_status,
        expansion.expansion_year,
        expansion.is_expansion_state,
        ahrq.rural_urban_code_2013,
        ahrq.is_rural

    from counties
    left join states    on counties.state_fips = states.state_fips
    left join expansion  on counties.state_fips = expansion.state_fips
    left join ahrq       on counties.county_fips = ahrq.county_fips
)

select
    county_fips,
    county_name,
    state_fips,
    state_name,
    state_abbr,
    census_region,
    census_division,
    expansion_status,
    expansion_year,
    is_expansion_state,
    rural_urban_code_2013,
    is_rural
from joined
