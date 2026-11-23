-- Data Contract Test: Liverpool University Hospitals NHS FT (ODS code REM) must be present in the feature mart
WITH rem_check AS (
    SELECT COUNT(*) AS rem_count
    FROM {{ ref('fct_trust_winter_pressure_daily') }}
    WHERE trust_code = 'REM'
)

SELECT *
FROM rem_check
WHERE rem_count = 0
