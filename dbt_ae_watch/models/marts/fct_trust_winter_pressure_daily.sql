WITH trust_weather AS (
    SELECT * FROM {{ ref('int_trust_weather_joined') }}
),

pathogen_lags AS (
    SELECT * FROM {{ ref('int_pathogen_epidemiology_lags') }}
)

SELECT
    tw.period_date,
    tw.trust_code,
    tw.trust_name,
    -- Activity Metrics
    tw.total_attendances,
    tw.type1_attendances,
    tw.total_over4hr,
    tw.type1_over4hr,
    tw.emergency_admissions,
    tw.over12hr_trolley_waits,
    -- Performance Indicators
    tw.performance_4hr_pct,
    tw.breach_4hr_pct,
    -- Weather Telemetry
    tw.monthly_avg_temp_c,
    tw.monthly_min_temp_c,
    tw.monthly_min_apparent_temp_c,
    tw.total_frost_days,
    tw.total_cold_snap_degree_days,
    tw.total_precipitation_mm,
    tw.max_wind_speed_kmh,
    -- Epidemiological Surveillance (Flu, RSV, Noro, COVID-19 & 111 Calls)
    p.flu_admission_rate,
    p.flu_positivity_pct,
    p.flu_admission_rate_lag_2w,
    p.rsv_admission_rate,
    p.rsv_positivity_pct,
    p.norovirus_total_cases,
    p.covid_positivity_pct,
    p.covid_admission_rate,
    p.nhs111_resp_calls_7d_avg,
    -- Operational Pressure Risk Classification
    CASE
        WHEN tw.performance_4hr_pct < 65.0 OR tw.over12hr_trolley_waits > 1000 THEN 'CRITICAL'
        WHEN tw.performance_4hr_pct < 75.0 OR tw.over12hr_trolley_waits > 500 THEN 'SEVERE'
        WHEN tw.performance_4hr_pct < 85.0 THEN 'ELEVATED'
        ELSE 'NORMAL'
    END AS operational_pressure_level,
    -- Attribution & Scope
    tw.is_cheshire_merseyside,
    tw.is_target_benchmark_trust,
    NOW() AS mart_created_at
FROM trust_weather tw
LEFT JOIN pathogen_lags p
    ON tw.period_date = p.period_month
