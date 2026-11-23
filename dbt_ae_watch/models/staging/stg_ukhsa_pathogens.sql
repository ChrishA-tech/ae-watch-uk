WITH ranked_records AS (
    SELECT
        theme,
        sub_theme,
        topic,
        metric,
        geography_type,
        geography_name,
        geography_code,
        metric_value,
        period_start,
        period_end,
        ingested_at,
        ROW_NUMBER() OVER (
            PARTITION BY topic, metric, geography_type, geography_name, period_start
            ORDER BY ingested_at DESC
        ) AS row_num
    FROM bronze.ukhsa_pathogens_raw
)

SELECT
    topic AS pathogen,
    metric,
    geography_type,
    geography_name,
    geography_code,
    metric_value,
    period_start,
    period_end,
    -- Flag regional proximity to target benchmark (North West)
    (geography_name = 'North West') AS is_north_west_region,
    ingested_at
FROM ranked_records
WHERE row_num = 1
