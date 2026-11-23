WITH ranked_records AS (
    SELECT
        period_date,
        org_code,
        org_name,
        type1_attendances,
        type2_attendances,
        type3_attendances,
        total_attendances,
        type1_over4hr,
        total_over4hr,
        emergency_admissions,
        over12hr_trolley_waits,
        raw_source_file,
        ingested_at,
        ROW_NUMBER() OVER (
            PARTITION BY org_code, period_date
            ORDER BY ingested_at DESC
        ) AS row_num
    FROM bronze.nhs_ae_raw
)

SELECT
    period_date,
    org_code,
    org_name,
    type1_attendances,
    type2_attendances,
    type3_attendances,
    total_attendances,
    type1_over4hr,
    total_over4hr,
    emergency_admissions,
    over12hr_trolley_waits,
    -- 4-hour performance percentage [0.0 - 100.0]
    CASE
        WHEN total_attendances > 0 THEN
            ROUND(((total_attendances - total_over4hr)::NUMERIC / total_attendances::NUMERIC) * 100.0, 2)
        ELSE 100.00
    END AS performance_4hr_pct,
    -- Breach rate percentage [0.0 - 100.0]
    CASE
        WHEN total_attendances > 0 THEN
            ROUND((total_over4hr::NUMERIC / total_attendances::NUMERIC) * 100.0, 2)
        ELSE 0.00
    END AS breach_4hr_pct,
    -- Trust Categorization & Flags
    (org_code IN ('REM', 'RJR', 'RBL', 'RWW', 'RBS', 'REP')) AS is_cheshire_merseyside,
    (org_code = 'REM') AS is_target_benchmark_trust,
    raw_source_file,
    ingested_at
FROM ranked_records
WHERE row_num = 1
