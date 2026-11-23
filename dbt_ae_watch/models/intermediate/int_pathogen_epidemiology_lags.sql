WITH weekly_pathogens AS (
    SELECT
        pathogen,
        metric,
        geography_name,
        period_start,
        DATE_TRUNC('month', period_start)::DATE AS period_month,
        metric_value,
        LAG(metric_value, 1) OVER (
            PARTITION BY pathogen, metric, geography_name
            ORDER BY period_start
        ) AS metric_value_lag_1w,
        LAG(metric_value, 2) OVER (
            PARTITION BY pathogen, metric, geography_name
            ORDER BY period_start
        ) AS metric_value_lag_2w,
        LAG(metric_value, 3) OVER (
            PARTITION BY pathogen, metric, geography_name
            ORDER BY period_start
        ) AS metric_value_lag_3w
    FROM {{ ref('stg_ukhsa_pathogens') }}
),

monthly_pathogen_summary AS (
    SELECT
        period_month,
        -- Influenza metrics
        ROUND(AVG(CASE WHEN pathogen = 'Influenza' AND metric LIKE '%hospitalAdmissionRate%' THEN metric_value END)::NUMERIC, 2) AS flu_admission_rate,
        ROUND(AVG(CASE WHEN pathogen = 'Influenza' AND metric LIKE '%positivity%' THEN metric_value END)::NUMERIC, 2) AS flu_positivity_pct,
        ROUND(AVG(CASE WHEN pathogen = 'Influenza' AND metric LIKE '%hospitalAdmissionRate%' THEN metric_value_lag_2w END)::NUMERIC, 2) AS flu_admission_rate_lag_2w,
        -- RSV metrics
        ROUND(AVG(CASE WHEN pathogen = 'RSV' AND metric LIKE '%hospitalAdmissionRate%' THEN metric_value END)::NUMERIC, 2) AS rsv_admission_rate,
        ROUND(AVG(CASE WHEN pathogen = 'RSV' AND metric LIKE '%positivity%' THEN metric_value END)::NUMERIC, 2) AS rsv_positivity_pct,
        -- Norovirus metrics
        ROUND(SUM(CASE WHEN pathogen = 'norovirus' THEN metric_value END)::NUMERIC, 2) AS norovirus_total_cases,
        -- COVID-19 PCR Positivity & Healthcare Burden
        ROUND(AVG(CASE WHEN pathogen = 'COVID-19' AND metric LIKE '%positivity%' THEN metric_value END)::NUMERIC, 2) AS covid_positivity_pct,
        ROUND(AVG(CASE WHEN pathogen = 'COVID-19' AND metric LIKE '%admission%' THEN metric_value END)::NUMERIC, 2) AS covid_admission_rate,
        -- NHS 111 Acute Respiratory Syndromic Calls
        ROUND(AVG(CASE WHEN metric LIKE '%NHS111%' THEN metric_value END)::NUMERIC, 2) AS nhs111_resp_calls_7d_avg
    FROM weekly_pathogens
    GROUP BY period_month
)

SELECT
    period_month,
    COALESCE(flu_admission_rate, 0.0) AS flu_admission_rate,
    COALESCE(flu_positivity_pct, 0.0) AS flu_positivity_pct,
    COALESCE(flu_admission_rate_lag_2w, 0.0) AS flu_admission_rate_lag_2w,
    COALESCE(rsv_admission_rate, 0.0) AS rsv_admission_rate,
    COALESCE(rsv_positivity_pct, 0.0) AS rsv_positivity_pct,
    COALESCE(norovirus_total_cases, 0.0) AS norovirus_total_cases,
    COALESCE(covid_positivity_pct, 0.0) AS covid_positivity_pct,
    COALESCE(covid_admission_rate, 0.0) AS covid_admission_rate,
    COALESCE(nhs111_resp_calls_7d_avg, 0.0) AS nhs111_resp_calls_7d_avg
FROM monthly_pathogen_summary
