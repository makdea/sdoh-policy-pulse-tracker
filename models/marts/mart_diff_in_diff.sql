{{
    config(
        materialized='table',
        description='Difference-in-differences estimates: expansion vs non-expansion states across era transitions.'
    )
}}

-- Classic 2×2 DiD for each era transition and each outcome.
--
-- treatment  = expansion states (is_expansion_state = true)
-- control    = non-expansion states (is_expansion_state = false)
-- pre-period = Trump1 (2017–2020)
-- post-period = Biden (2021–2022, limited by SAHIE availability)
--
-- DiD = (post_treated - pre_treated) - (post_control - pre_control)
--
-- Positive DiD for pct_uninsured means treated states saw MORE improvement
-- (larger decrease) than control states — the expected sign if expansion works.

with base as (
    select * from {{ ref('int_medicaid_exposure') }}
    where era_name in ('Trump1', 'Biden')
      and pct_uninsured is not null
),

-- Era × treatment cell averages
cell_avgs as (
    select
        era_name,
        is_expansion_state,
        count(distinct county_fips)          as n_counties,
        count(*)                             as n_obs,
        avg(pct_uninsured)                   as avg_pct_uninsured,
        avg(unemployment_rate)               as avg_unemployment_rate,
        avg(poverty_rate)                    as avg_poverty_rate,
        avg(median_household_income)         as avg_median_hh_income,
        avg(pct_bachelors_plus)              as avg_pct_bachelors_plus
    from base
    group by era_name, is_expansion_state
),

-- Pivot to one row per treatment group
pivoted as (
    select
        is_expansion_state,
        n_counties,
        n_obs,

        max(case when era_name = 'Trump1' then avg_pct_uninsured    end) as trump1_pct_uninsured,
        max(case when era_name = 'Biden'  then avg_pct_uninsured    end) as biden_pct_uninsured,

        max(case when era_name = 'Trump1' then avg_unemployment_rate end) as trump1_unemployment,
        max(case when era_name = 'Biden'  then avg_unemployment_rate end) as biden_unemployment,

        max(case when era_name = 'Trump1' then avg_poverty_rate      end) as trump1_poverty_rate,
        max(case when era_name = 'Biden'  then avg_poverty_rate      end) as biden_poverty_rate,

        max(case when era_name = 'Trump1' then avg_median_hh_income  end) as trump1_median_income,
        max(case when era_name = 'Biden'  then avg_median_hh_income  end) as biden_median_income

    from cell_avgs
    group by is_expansion_state, n_counties, n_obs
),

-- Compute within-group changes
with_changes as (
    select
        *,
        biden_pct_uninsured    - trump1_pct_uninsured    as change_pct_uninsured,
        biden_unemployment     - trump1_unemployment      as change_unemployment,
        biden_poverty_rate     - trump1_poverty_rate      as change_poverty_rate,
        biden_median_income    - trump1_median_income     as change_median_income
    from pivoted
),

-- DiD = treated change minus control change
did as (
    select
        'pct_uninsured'     as outcome,
        t.trump1_pct_uninsured  as treated_pre,
        t.biden_pct_uninsured   as treated_post,
        c.trump1_pct_uninsured  as control_pre,
        c.biden_pct_uninsured   as control_post,
        t.change_pct_uninsured  as treated_change,
        c.change_pct_uninsured  as control_change,
        t.change_pct_uninsured - c.change_pct_uninsured as did_estimate,
        t.n_counties            as n_treated_counties,
        c.n_counties            as n_control_counties
    from with_changes t
    cross join with_changes c
    where t.is_expansion_state = true and c.is_expansion_state = false

    union all

    select
        'unemployment_rate'  as outcome,
        t.trump1_unemployment  as treated_pre,
        t.biden_unemployment   as treated_post,
        c.trump1_unemployment  as control_pre,
        c.biden_unemployment   as control_post,
        t.change_unemployment  as treated_change,
        c.change_unemployment  as control_change,
        t.change_unemployment - c.change_unemployment as did_estimate,
        t.n_counties           as n_treated_counties,
        c.n_counties           as n_control_counties
    from with_changes t
    cross join with_changes c
    where t.is_expansion_state = true and c.is_expansion_state = false

    union all

    select
        'poverty_rate'       as outcome,
        t.trump1_poverty_rate  as treated_pre,
        t.biden_poverty_rate   as treated_post,
        c.trump1_poverty_rate  as control_pre,
        c.biden_poverty_rate   as control_post,
        t.change_poverty_rate  as treated_change,
        c.change_poverty_rate  as control_change,
        t.change_poverty_rate - c.change_poverty_rate as did_estimate,
        t.n_counties           as n_treated_counties,
        c.n_counties           as n_control_counties
    from with_changes t
    cross join with_changes c
    where t.is_expansion_state = true and c.is_expansion_state = false

    union all

    select
        'median_household_income' as outcome,
        t.trump1_median_income  as treated_pre,
        t.biden_median_income   as treated_post,
        c.trump1_median_income  as control_pre,
        c.biden_median_income   as control_post,
        t.change_median_income  as treated_change,
        c.change_median_income  as control_change,
        t.change_median_income - c.change_median_income as did_estimate,
        t.n_counties            as n_treated_counties,
        c.n_counties            as n_control_counties
    from with_changes t
    cross join with_changes c
    where t.is_expansion_state = true and c.is_expansion_state = false
),

final as (
    select
        *,
        -- Negative DiD on pct_uninsured = expansion states improved more (good)
        -- Positive DiD on median_income = expansion states gained more income (good)
        case
            when outcome in ('pct_uninsured', 'unemployment_rate', 'poverty_rate')
            then 'lower is better — negative DiD favors expansion states'
            when outcome = 'median_household_income'
            then 'higher is better — positive DiD favors expansion states'
        end as interpretation_note,

        round(did_estimate * 100, 2) as did_estimate_pct_pts
    from did
)

select * from final
