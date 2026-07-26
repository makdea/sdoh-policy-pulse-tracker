{{
    config(
        materialized='view',
        description='Adds Medicaid expansion status and years-since-expansion to each county-year.'
    )
}}

-- Medicaid expansion creates a natural quasi-experiment:
--   treatment = expansion states (ACA Medicaid expansion adopted)
--   control   = non-expansion states
-- years_since_expansion enables dose-response analysis within the treated group.

with era_assigned as (
    select * from {{ ref('int_policy_era_assignments') }}
),

expansion as (
    select
        state_fips,
        expansion_status,
        -- expansion_year is null for non-expansion states
        safe_cast(expansion_year as integer) as expansion_year
    from {{ ref('medicaid_expansion_status') }}
),

joined as (
    select
        era_assigned.*,

        -- Expansion metadata
        expansion.expansion_status,
        expansion.expansion_year,
        case when expansion.expansion_status = 'expanded' then true else false end
            as is_expansion_state,

        -- Years since expansion at time of observation (0 in expansion year)
        -- Null for non-expansion states and pre-expansion years
        case
            when expansion.expansion_status = 'expanded'
             and era_assigned.year >= expansion.expansion_year
            then era_assigned.year - expansion.expansion_year
        end as years_since_expansion,

        -- Pre/post expansion indicator (for DiD treatment variable)
        case
            when expansion.expansion_status = 'not_expanded' then 'never_expanded'
            when era_assigned.year < expansion.expansion_year then 'pre_expansion'
            when era_assigned.year = expansion.expansion_year then 'expansion_year'
            else                                            'post_expansion'
        end as expansion_phase

    from era_assigned
    left join expansion using (state_fips)
)

select
    county_year_key,
    county_fips,
    state_fips,
    county_name,
    state_name,
    state_abbr,
    census_region,
    census_division,
    year,
    pct_uninsured,
    n_uninsured,
    n_insured,
    sahie_total_population,
    unemployment_rate,
    median_household_income,
    poverty_rate,
    pct_bachelors_plus,
    pct_hs_plus,
    pct_severe_rent_burden,
    dist_trauma_center_miles,
    mds_rate_per_100k,
    rural_urban_code_2013,
    is_rural,
    era_name,
    president,
    era_color_hex,
    policy_event_label,
    expansion_status,
    expansion_year,
    is_expansion_state,
    years_since_expansion,
    expansion_phase
from joined
