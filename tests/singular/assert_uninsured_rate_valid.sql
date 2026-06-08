-- Uninsured rate must be between 0 and 1 wherever non-null.
-- Fails if any row violates the constraint.

select
    county_fips,
    year,
    pct_uninsured
from {{ ref('mart_county_sdoh_trends') }}
where pct_uninsured is not null
  and (pct_uninsured < 0 or pct_uninsured > 1)
