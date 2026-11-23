WITH monthly_weather AS (
    SELECT
        trust_code,
        DATE_TRUNC('month', record_date)::DATE AS period_date,
        ROUND(AVG(temp_mean_c)::NUMERIC, 2) AS monthly_avg_temp_c,
        ROUND(MIN(temp_min_c)::NUMERIC, 2) AS monthly_min_temp_c,
        ROUND(MIN(apparent_temp_min_c)::NUMERIC, 2) AS monthly_min_apparent_temp_c,
        SUM(is_frost_day) AS total_frost_days,
        ROUND(SUM(cold_snap_degree_days)::NUMERIC, 2) AS total_cold_snap_degree_days,
        ROUND(SUM(precipitation_sum_mm)::NUMERIC, 2) AS total_precipitation_mm,
        MAX(wind_speed_max_kmh) AS max_wind_speed_kmh
    FROM {{ ref('stg_weather_daily') }}
    GROUP BY trust_code, DATE_TRUNC('month', record_date)::DATE
)

SELECT
    ae.period_date,
    ae.org_code AS trust_code,
    ae.org_name AS trust_name,
    ae.total_attendances,
    ae.type1_attendances,
    ae.total_over4hr,
    ae.type1_over4hr,
    ae.performance_4hr_pct,
    ae.breach_4hr_pct,
    ae.emergency_admissions,
    ae.over12hr_trolley_waits,
    ae.is_cheshire_merseyside,
    ae.is_target_benchmark_trust,
    w.monthly_avg_temp_c,
    w.monthly_min_temp_c,
    w.monthly_min_apparent_temp_c,
    w.total_frost_days,
    w.total_cold_snap_degree_days,
    w.total_precipitation_mm,
    w.max_wind_speed_kmh
FROM {{ ref('stg_nhs_ae_attendances') }} ae
LEFT JOIN monthly_weather w
    ON ae.org_code = w.trust_code
    AND ae.period_date = w.period_date
