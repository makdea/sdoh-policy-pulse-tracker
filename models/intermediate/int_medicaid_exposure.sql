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
        try_cast(expansion_year as integer) as expansion_year
    from {{ ref('medicaid_expansion_status') }}
),

joined as (
    select
        e.*,

        -- Expansion metadata
        ex.expansion_status,
        ex.expansion_year,
        case when ex.expansion_status = 'expanded' then true else false end
            as is_expansion_state,

        -- Years since expansion at time of observation (0 in expansion year)
        -- Null for non-expansion states and pre-expansion years
        case
            when ex.expansion_status = 'expanded'
             and e.year >= ex.expansion_year
            then e.year - ex.expansion_year
        end as years_since_expansion,

        -- Pre/post expansion indicator (for DiD treatment variable)
        case
            when ex.expansion_status = 'not_expanded' then 'never_expanded'
            when e.year < ex.expansion_year            then 'pre_expansion'
            when e.year = ex.expansion_year            then 'expansion_year'
            else                                            'post_expansion'
        end as expansion_phase

    from era_assigned e
    left join expansion ex using (state_fips)
)

select * from joined
