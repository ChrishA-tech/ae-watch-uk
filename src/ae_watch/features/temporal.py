"""Temporal and Autoregressive Feature Engineering for AE-Watch UK.

Computes epidemiological pathogen lags, rolling cold-snap degree days,
UK bank-holiday/calendar flags, and autoregressive breach-rate rolling windows.
Materializes gold.ml_trust_forecast_features in PostgreSQL.
Author: CHRISH PEP FELIX A
"""

import math
from calendar import monthrange
from datetime import date

import holidays
import polars as pl
import psycopg

from ae_watch.config import settings
from ae_watch.features.spatial import compute_idw_catchment_spillover
from ae_watch.utils.logger import logger

UK_HOLIDAYS = holidays.country_holidays("UK")


def get_bank_holidays_in_month(year: int, month: int) -> int:
    """Return count of official UK bank holidays in a given year and month."""
    _, num_days = monthrange(year, month)
    count = 0
    for day in range(1, num_days + 1):
        d = date(year, month, day)
        if d in UK_HOLIDAYS:
            count += 1
    return count


class FeaturePipeline:
    """End-to-end feature pipeline generating gold.ml_trust_forecast_features."""

    def __init__(self, pg_conn_uri: str | None = None):
        self.pg_conn_uri = pg_conn_uri or settings.postgres_connection_uri

    def load_gold_mart_data(self) -> pl.DataFrame:
        """Load curated data from gold.fct_trust_winter_pressure_daily."""
        logger.info("loading_gold_mart_for_feature_engineering")
        with psycopg.connect(self.pg_conn_uri) as conn:
            query = """
                SELECT
                    period_date,
                    trust_code,
                    trust_name,
                    total_attendances,
                    type1_attendances,
                    total_over4hr,
                    type1_over4hr,
                    performance_4hr_pct,
                    breach_4hr_pct,
                    monthly_avg_temp_c,
                    monthly_min_temp_c,
                    monthly_min_apparent_temp_c,
                    total_frost_days,
                    total_cold_snap_degree_days,
                    total_precipitation_mm,
                    max_wind_speed_kmh,
                    flu_admission_rate,
                    flu_positivity_pct,
                    flu_admission_rate_lag_2w,
                    rsv_admission_rate,
                    rsv_positivity_pct,
                    norovirus_total_cases,
                    covid_positivity_pct,
                    covid_admission_rate,
                    nhs111_resp_calls_7d_avg,
                    is_cheshire_merseyside,
                    is_target_benchmark_trust
                FROM gold.fct_trust_winter_pressure_daily
                ORDER BY trust_code, period_date ASC;
            """
            with conn.cursor() as cur:
                cur.execute(query)
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()

        # Convert Decimals/dates to float/date cleanly
        clean_rows = []
        for r in rows:
            clean_rows.append(
                {
                    col: float(val) if hasattr(val, "as_tuple") else val
                    for col, val in zip(columns, r)
                }
            )

        return pl.from_dicts(clean_rows, infer_schema_length=None)

    def engineer_features(self, df: pl.DataFrame) -> pl.DataFrame:
        """Apply spatial IDW, temporal lags, calendar indicators, and autoregressive terms."""
        logger.info("engineering_temporal_and_autoregressive_features", rows=len(df))

        # 1. Compute Spatial IDW Spillover for Liverpool REM
        rem_spillover_df = compute_idw_catchment_spillover(df, target_trust="REM", radius_km=25.0)

        # 2. Join IDW spillover back to full dataset
        df = df.join(
            rem_spillover_df.select(
                [
                    "period_date",
                    "trust_code",
                    "idw_neighbor_breach_rate",
                    "idw_neighbor_attendance_pressure",
                    "active_neighbors_count",
                    "h3_res7_cell",
                ]
            ),
            on=["period_date", "trust_code"],
            how="left",
        )

        # Fill nulls for non-REM trusts with zero
        df = df.with_columns(
            [
                pl.col("idw_neighbor_breach_rate").fill_null(0.0),
                pl.col("idw_neighbor_attendance_pressure").fill_null(0.0),
                pl.col("active_neighbors_count").fill_null(0),
                pl.col("h3_res7_cell").fill_null("unknown"),
            ]
        )

        # 3. Calendar & Holiday Features
        period_dates = df["period_date"].to_list()
        sin_months = []
        cos_months = []
        is_winter = []
        bank_holidays = []

        for p_date in period_dates:
            m = p_date.month
            y = p_date.year
            sin_months.append(round(math.sin(2.0 * math.pi * m / 12.0), 4))
            cos_months.append(round(math.cos(2.0 * math.pi * m / 12.0), 4))
            is_winter.append(1 if m in {11, 12, 1, 2, 3} else 0)
            bank_holidays.append(get_bank_holidays_in_month(y, m))

        df = df.with_columns(
            [
                pl.Series("sin_month", sin_months),
                pl.Series("cos_month", cos_months),
                pl.Series("is_winter_surge_period", is_winter),
                pl.Series("bank_holiday_count", bank_holidays),
            ]
        )

        # 4. Autoregressive Rolling Features per Trust (zero lookahead!)
        # Partition by trust_code and compute lags and rolling windows
        df = df.sort(["trust_code", "period_date"])

        df = df.with_columns(
            [
                # Autoregressive Lags (past observations only)
                pl.col("breach_4hr_pct").shift(1).over("trust_code").alias("breach_rate_lag_1m"),
                pl.col("breach_4hr_pct").shift(2).over("trust_code").alias("breach_rate_lag_2m"),
                pl.col("total_attendances").shift(1).over("trust_code").alias("attendances_lag_1m"),
                # Rolling 3-month statistics of past values (shifted by 1 to prevent leakage)
                pl.col("breach_4hr_pct")
                .shift(1)
                .rolling_mean(window_size=3, min_samples=1)
                .over("trust_code")
                .alias("breach_rolling_3m_mean"),
                pl.col("breach_4hr_pct")
                .shift(1)
                .rolling_max(window_size=3, min_samples=1)
                .over("trust_code")
                .alias("breach_rolling_3m_max"),
                pl.col("breach_4hr_pct")
                .shift(1)
                .rolling_std(window_size=3, min_samples=1)
                .over("trust_code")
                .alias("breach_rolling_3m_std"),
                # Multi-Horizon Forecasting Targets (future observations)
                pl.col("breach_4hr_pct")
                .shift(-1)
                .over("trust_code")
                .alias("target_breach_rate_horizon_7d"),
                pl.col("breach_4hr_pct")
                .shift(-2)
                .over("trust_code")
                .alias("target_breach_rate_horizon_14d"),
                pl.col("total_attendances")
                .shift(-1)
                .over("trust_code")
                .alias("target_attendances_horizon_7d"),
            ]
        )

        # Binary Surge Classification Target (1 if breach rate exceeds 30% or performance drops below 70%)
        df = df.with_columns(
            [
                pl.when(pl.col("target_breach_rate_horizon_7d") > 30.0)
                .then(1)
                .otherwise(0)
                .alias("target_surge_binary_7d"),
            ]
        )

        # 5. Sanitize NaNs and Infinities
        df = df.with_columns(
            [
                pl.col("breach_rate_lag_1m").fill_null(pl.col("breach_4hr_pct")),
                pl.col("breach_rate_lag_2m").fill_null(pl.col("breach_4hr_pct")),
                pl.col("attendances_lag_1m").fill_null(pl.col("total_attendances")),
                pl.col("breach_rolling_3m_mean").fill_null(pl.col("breach_4hr_pct")),
                pl.col("breach_rolling_3m_max").fill_null(pl.col("breach_4hr_pct")),
                pl.col("breach_rolling_3m_std").fill_null(0.0),
            ]
        )

        return df

    def materialize_feature_store(self, df: pl.DataFrame) -> int:
        """Create and populate gold.ml_trust_forecast_features in PostgreSQL."""
        logger.info("materializing_gold_ml_trust_forecast_features", rows=len(df))

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS gold.ml_trust_forecast_features (
            period_date DATE NOT NULL,
            trust_code VARCHAR(16) NOT NULL,
            trust_name VARCHAR(255) NOT NULL,
            total_attendances DOUBLE PRECISION,
            type1_attendances DOUBLE PRECISION,
            total_over4hr DOUBLE PRECISION,
            type1_over4hr DOUBLE PRECISION,
            performance_4hr_pct DOUBLE PRECISION,
            breach_4hr_pct DOUBLE PRECISION,
            idw_neighbor_breach_rate DOUBLE PRECISION,
            idw_neighbor_attendance_pressure DOUBLE PRECISION,
            active_neighbors_count INTEGER,
            h3_res7_cell VARCHAR(32),
            monthly_avg_temp_c DOUBLE PRECISION,
            monthly_min_temp_c DOUBLE PRECISION,
            monthly_min_apparent_temp_c DOUBLE PRECISION,
            total_frost_days DOUBLE PRECISION,
            total_cold_snap_degree_days DOUBLE PRECISION,
            total_precipitation_mm DOUBLE PRECISION,
            max_wind_speed_kmh DOUBLE PRECISION,
            flu_admission_rate DOUBLE PRECISION,
            flu_positivity_pct DOUBLE PRECISION,
            flu_admission_rate_lag_2w DOUBLE PRECISION,
            rsv_admission_rate DOUBLE PRECISION,
            rsv_positivity_pct DOUBLE PRECISION,
            norovirus_total_cases DOUBLE PRECISION,
            covid_positivity_pct DOUBLE PRECISION,
            covid_admission_rate DOUBLE PRECISION,
            nhs111_resp_calls_7d_avg DOUBLE PRECISION,
            sin_month DOUBLE PRECISION,
            cos_month DOUBLE PRECISION,
            is_winter_surge_period INTEGER,
            bank_holiday_count INTEGER,
            breach_rate_lag_1m DOUBLE PRECISION,
            breach_rate_lag_2m DOUBLE PRECISION,
            attendances_lag_1m DOUBLE PRECISION,
            breach_rolling_3m_mean DOUBLE PRECISION,
            breach_rolling_3m_max DOUBLE PRECISION,
            breach_rolling_3m_std DOUBLE PRECISION,
            target_breach_rate_horizon_7d DOUBLE PRECISION,
            target_breach_rate_horizon_14d DOUBLE PRECISION,
            target_attendances_horizon_7d DOUBLE PRECISION,
            target_surge_binary_7d INTEGER,
            is_cheshire_merseyside BOOLEAN,
            is_target_benchmark_trust BOOLEAN,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (trust_code, period_date)
        );
        """

        with psycopg.connect(self.pg_conn_uri) as conn, conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS gold.ml_trust_forecast_features CASCADE;")
            cur.execute(create_table_sql)

            # Insert all rows
            columns = [c for c in df.columns if c != "created_at"]
            placeholders = ", ".join(["%s"] * len(columns))
            cols_str = ", ".join(columns)

            insert_sql = f"""
                INSERT INTO gold.ml_trust_forecast_features ({cols_str})
                VALUES ({placeholders})
                ON CONFLICT (trust_code, period_date) DO UPDATE
                SET breach_4hr_pct = EXCLUDED.breach_4hr_pct;
            """

            for row in df.iter_rows():
                # Replace None or NaN with 0.0 for numeric columns where appropriate
                sanitized = [0.0 if isinstance(v, float) and math.isnan(v) else v for v in row]
                cur.execute(insert_sql, sanitized)

            conn.commit()

        logger.info("feature_store_materialized_successfully", total_records=len(df))
        return len(df)

    def run(self) -> pl.DataFrame:
        """Execute full feature engineering and materialization pipeline."""
        df_raw = self.load_gold_mart_data()
        df_features = self.engineer_features(df_raw)
        self.materialize_feature_store(df_features)
        return df_features


feature_pipeline = FeaturePipeline()

if __name__ == "__main__":
    feature_pipeline.run()
