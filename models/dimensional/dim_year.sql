{{
    config(
        materialized='table',
        description='Year dimension: political era, president, and policy-event labels.'
    )
}}

-- Grain: year. One row per calendar year in the study window (2017-2025),
-- lifted out of what was previously the policy_events CTE + policy_eras
-- seed join inside int_policy_era_assignments.sql.

with years as (
    select year
    from unnest(generate_array(2017, 2025)) as year
),

eras as (
    select
        era_name,
        president,
        start_year,
        end_year,
        color_hex
    from {{ ref('policy_eras') }}
),

policy_events as (
    select
        year,
        case
            when year = 2019 then 'ACA individual mandate penalty repealed'
            when year = 2020 then 'COVID-19: continuous coverage requirement (Mar)'
            when year = 2021 then 'American Rescue Plan ACA subsidy expansion'
            when year = 2023 then 'Medicaid unwinding begins (Apr)'
            when year = 2024 then 'Medicaid unwinding ends (Jun); enrollment drops'
            when year = 2025 then 'Trump2 Medicaid work requirements / DOGE cuts'
        end as policy_event_label
    from years
),

joined as (
    select
        years.year,
        eras.era_name,
        eras.president,
        eras.color_hex as era_color_hex,
        pol.policy_event_label

    from years
    left join eras
        on years.year between eras.start_year and eras.end_year
    left join policy_events pol
        on years.year = pol.year
)

select
    year,
    era_name,
    president,
    era_color_hex,
    policy_event_label
from joined
