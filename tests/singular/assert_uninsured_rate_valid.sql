-- n_uninsured must never exceed sahie_total_population, and both must be
-- non-negative wherever non-null -- otherwise the weighted uninsurance
-- ratio metric (SUM(n_uninsured)/SUM(sahie_total_population)) would fall
-- outside [0, 1].

select
    county_fips,
    year,
    n_uninsured,
    sahie_total_population
from {{ ref('fct_county_year_sdoh') }}
where n_uninsured is not null
  and sahie_total_population is not null
  and (
    n_uninsured < 0
    or sahie_total_population < 0
    or n_uninsured > sahie_total_population
  )
