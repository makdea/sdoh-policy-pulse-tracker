-- Analysis: which counties saw the sharpest SDOH deterioration between eras?
-- Compares each county's population-weighted uninsurance rate in Trump1 vs Biden.
-- Run with: dbt compile --profiles-dir . && dbt show --select era_change_summary

with fact as (
    select
        fct.county_fips,
        dim_county.county_name,
        dim_county.state_abbr,
        dim_county.is_expansion_state,
        dim_year.era_name,
        fct.n_uninsured,
        fct.sahie_total_population,
        fct.n_below_poverty,
        fct.poverty_universe,
        fct.unemployment_level,
        fct.labor_force_level
    from {{ ref('fct_county_year_sdoh') }} fct
    inner join {{ ref('dim_county') }} dim_county on fct.county_fips = dim_county.county_fips
    inner join {{ ref('dim_year') }} dim_year on fct.year = dim_year.year
    where dim_year.era_name in ('Trump1', 'Biden')
      and fct.n_uninsured is not null
),

trump1 as (
    select
        county_fips,
        any_value(county_name)         as county_name,
        any_value(state_abbr)          as state_abbr,
        any_value(is_expansion_state)  as is_expansion_state,
        safe_divide(sum(n_uninsured), sum(sahie_total_population))       as weighted_pct_uninsured,
        safe_divide(sum(n_below_poverty), sum(poverty_universe))         as weighted_poverty_rate,
        safe_divide(sum(unemployment_level), sum(labor_force_level))     as weighted_unemployment_rate
    from fact
    where era_name = 'Trump1'
    group by county_fips
),

biden as (
    select
        county_fips,
        safe_divide(sum(n_uninsured), sum(sahie_total_population))       as weighted_pct_uninsured,
        safe_divide(sum(n_below_poverty), sum(poverty_universe))         as weighted_poverty_rate,
        safe_divide(sum(unemployment_level), sum(labor_force_level))     as weighted_unemployment_rate
    from fact
    where era_name = 'Biden'
    group by county_fips
),

compared as (
    select
        t.county_fips,
        t.county_name,
        t.state_abbr,
        t.is_expansion_state,
        t.weighted_pct_uninsured                                    as trump1_pct_uninsured,
        b.weighted_pct_uninsured                                    as biden_pct_uninsured,
        b.weighted_pct_uninsured - t.weighted_pct_uninsured         as change_pct_uninsured,
        t.weighted_poverty_rate                                     as trump1_poverty_rate,
        b.weighted_poverty_rate                                     as biden_poverty_rate,
        b.weighted_poverty_rate - t.weighted_poverty_rate           as change_poverty_rate

    from trump1 t
    inner join biden b using (county_fips)
)

select
    *,
    case
        when change_pct_uninsured > 0.01  then 'deteriorated'
        when change_pct_uninsured < -0.01 then 'improved'
        else 'stable'
    end as uninsurance_trajectory
from compared
order by change_pct_uninsured desc  -- most deteriorated first
limit 50
