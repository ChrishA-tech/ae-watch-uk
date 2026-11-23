WITH ranked_records AS (
    SELECT
        trust_code,
        hospital_name,
        latitude,
        longitude,
        record_date,
        temp_min_c,
        temp_mean_c,
        temp_max_c,
        apparent_temp_min_c,
        wind_speed_max_kmh,
        precipitation_sum_mm,
        is_forecast,
        ingested_at,
        ROW_NUMBER() OVER (
            PARTITION BY trust_code, hospital_name, record_date
            ORDER BY ingested_at DESC
        ) AS row_num
    FROM bronze.open_meteo_raw
)

SELECT
    trust_code,
    hospital_name,
    latitude,
    longitude,
    record_date,
    temp_min_c,
    temp_mean_c,
    temp_max_c,
    apparent_temp_min_c,
    wind_speed_max_kmh,
    precipitation_sum_mm,
    -- Cold-snap degree days: degree deficit below 5°C threshold
    ROUND(GREATEST(0.0, 5.0 - COALESCE(temp_mean_c, 5.0))::NUMERIC, 2) AS cold_snap_degree_days,
    -- Frost day indicator (sub-zero minimum temperature)
    CASE WHEN temp_min_c < 0.0 THEN 1 ELSE 0 END AS is_frost_day,
    -- Target trust flag
    (trust_code = 'REM') AS is_target_benchmark_trust,
    is_forecast,
    ingested_at
FROM ranked_records
WHERE row_num = 1
