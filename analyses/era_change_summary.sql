-- Analysis: which counties saw the sharpest SDOH deterioration between eras?
-- Compares each county's average uninsurance rate in Trump1 vs Biden.
-- Run with: dbt compile --profiles-dir . && dbt show --select era_change_summary

with trump1 as (
    select
        county_fips,
        county_name,
        state_abbr,
        is_expansion_state,
        avg(pct_uninsured)    as avg_pct_uninsured,
        avg(poverty_rate)     as avg_poverty_rate,
        avg(unemployment_rate) as avg_unemployment_rate
    from {{ ref('mart_county_sdoh_trends') }}
    where era_name = 'Trump1'
      and pct_uninsured is not null
    group by county_fips, county_name, state_abbr, is_expansion_state
),

biden as (
    select
        county_fips,
        avg(pct_uninsured)    as avg_pct_uninsured,
        avg(poverty_rate)     as avg_poverty_rate,
        avg(unemployment_rate) as avg_unemployment_rate
    from {{ ref('mart_county_sdoh_trends') }}
    where era_name = 'Biden'
      and pct_uninsured is not null
    group by county_fips
),

compared as (
    select
        t.county_fips,
        t.county_name,
        t.state_abbr,
        t.is_expansion_state,
        t.avg_pct_uninsured                                 as trump1_pct_uninsured,
        b.avg_pct_uninsured                                 as biden_pct_uninsured,
        b.avg_pct_uninsured - t.avg_pct_uninsured           as change_pct_uninsured,
        t.avg_poverty_rate                                  as trump1_poverty_rate,
        b.avg_poverty_rate                                  as biden_poverty_rate,
        b.avg_poverty_rate - t.avg_poverty_rate             as change_poverty_rate

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
