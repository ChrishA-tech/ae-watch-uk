-- Data Contract Test: 4-hour performance percentage must strictly be within [0.0, 100.0]
SELECT
    period_date,
    trust_code,
    performance_4hr_pct
FROM {{ ref('fct_trust_winter_pressure_daily') }}
WHERE performance_4hr_pct < 0.0 OR performance_4hr_pct > 100.0
