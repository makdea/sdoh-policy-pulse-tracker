-- DiD mart must have exactly 4 outcome rows (one per metric).
-- Fails if any outcome is missing, indicating upstream join failure.

with expected as (
    select * from unnest(['pct_uninsured','unemployment_rate','poverty_rate','median_household_income']) as outcome
),
actual as (
    select outcome from {{ ref('mart_diff_in_diff') }}
)
select e.outcome
from expected e
left join actual a using (outcome)
where a.outcome is null
