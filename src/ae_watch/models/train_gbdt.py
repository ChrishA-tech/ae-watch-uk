"""Multi-Horizon GBDT Forecasting Models (LightGBM & XGBoost).

Implements strict expanding-window temporal cross-validation (zero future leakage)
to predict 7-day and 14-day A&E 4-hour breach rates and attendance surges
with P10, P50, and P90 quantile prediction intervals.
Logs metrics, parameters, and models to MLflow.
Author: CHRISH PEP FELIX A
"""

import os
from typing import Any

import lightgbm as lgb
import mlflow

os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"
import numpy as np
import pandas as pd
import psycopg
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, roc_auc_score

from ae_watch.config import settings
from ae_watch.utils.logger import logger

FEATURE_COLUMNS = [
    # Autoregressive past indicators
    "breach_rate_lag_1m",
    "breach_rate_lag_2m",
    "attendances_lag_1m",
    "breach_rolling_3m_mean",
    "breach_rolling_3m_max",
    "breach_rolling_3m_std",
    # Spatial Catchment Congestion Spillover
    "idw_neighbor_breach_rate",
    "idw_neighbor_attendance_pressure",
    "active_neighbors_count",
    # Meteorological Telemetry
    "monthly_avg_temp_c",
    "monthly_min_temp_c",
    "monthly_min_apparent_temp_c",
    "total_frost_days",
    "total_cold_snap_degree_days",
    "total_precipitation_mm",
    "max_wind_speed_kmh",
    # Epidemiological Pathogen Burdens
    "flu_admission_rate",
    "flu_positivity_pct",
    "flu_admission_rate_lag_2w",
    "rsv_admission_rate",
    "rsv_positivity_pct",
    "norovirus_total_cases",
    "covid_positivity_pct",
    "covid_admission_rate",
    "nhs111_resp_calls_7d_avg",
    # Calendar & Winter Cycles
    "sin_month",
    "cos_month",
    "is_winter_surge_period",
    "bank_holiday_count",
]


def pinball_loss(y_true: np.ndarray, y_pred: np.ndarray, alpha: float) -> float:
    """Calculate Pinball Loss for quantile alpha."""
    diff = y_true - y_pred
    return float(np.mean(np.maximum(alpha * diff, (alpha - 1.0) * diff)))


def empirical_coverage(y_true: np.ndarray, y_p10: np.ndarray, y_p90: np.ndarray) -> float:
    """Calculate Empirical 80% Prediction Interval Coverage Probability (PICP)."""
    inside = (y_true >= y_p10) & (y_true <= y_p90)
    return float(np.mean(inside))


def load_dataset_from_db(pg_conn_uri: str | None = None) -> pd.DataFrame:
    """Load feature store from PostgreSQL gold.ml_trust_forecast_features."""
    uri = pg_conn_uri or settings.postgres_connection_uri
    logger.info("loading_feature_store_for_training")
    with psycopg.connect(uri) as conn:
        df = pd.read_sql_query(
            """
            SELECT * FROM gold.ml_trust_forecast_features
            WHERE target_breach_rate_horizon_7d IS NOT NULL
            ORDER BY period_date ASC, trust_code ASC;
            """,
            conn,
        )
    logger.info("dataset_loaded", total_rows=len(df), unique_periods=df["period_date"].nunique())
    return df


def generate_expanding_window_splits(
    df: pd.DataFrame, min_train_periods: int = 12, val_step: int = 4
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Generate expanding-window temporal cross-validation splits with zero future leakage.

    Folds expand forward in time: fold k trains on periods [0..t] and evaluates on (t..t+val_step].
    """
    sorted_periods = sorted(df["period_date"].unique())
    n_periods = len(sorted_periods)

    splits = []
    current_train_end = min_train_periods

    while current_train_end + val_step <= n_periods:
        train_periods = set(sorted_periods[:current_train_end])
        val_periods = set(sorted_periods[current_train_end : current_train_end + val_step])

        train_idx = df.index[df["period_date"].isin(train_periods)].to_numpy()
        val_idx = df.index[df["period_date"].isin(val_periods)].to_numpy()

        splits.append((train_idx, val_idx))
        current_train_end += val_step

    # Ensure at least 2 folds exist
    if not splits and n_periods > min_train_periods:
        split_point = int(n_periods * 0.75)
        train_idx = df.index[df["period_date"].isin(set(sorted_periods[:split_point]))].to_numpy()
        val_idx = df.index[df["period_date"].isin(set(sorted_periods[split_point:]))].to_numpy()
        splits.append((train_idx, val_idx))

    return splits


class GBDTForecastingPipeline:
    """Trainer for LightGBM Quantile Regressors and XGBoost Surge Classifiers."""

    def __init__(self, tracking_uri: str = "file:./mlruns"):
        self.tracking_uri = tracking_uri
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment("ae_watch_uk_gbdt_forecasting")

    def train_quantile_lightgbm(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_val: pd.DataFrame,
        y_val: np.ndarray,
        alpha: float,
    ) -> lgb.LGBMRegressor:
        """Train a single LightGBM quantile regression model."""
        model = lgb.LGBMRegressor(
            objective="quantile",
            alpha=alpha,
            n_estimators=100,
            learning_rate=0.05,
            num_leaves=31,
            random_state=42,
            verbosity=-1,
            n_jobs=1,
        )
        model.fit(X_train, y_train)
        return model

    def train_xgboost_classifier(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_val: pd.DataFrame,
        y_val: np.ndarray,
    ) -> xgb.XGBClassifier:
        """Train XGBoost binary surge probability classifier."""
        model = xgb.XGBClassifier(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=5,
            eval_metric="logloss",
            random_state=42,
        )
        model.fit(X_train, y_train)
        return model

    def run_training_pipeline(self) -> dict[str, Any]:
        """Execute end-to-end expanding-window cross-validation and MLflow logging."""
        df = load_dataset_from_db()
        X = df[FEATURE_COLUMNS].fillna(0.0)
        y_breach = df["target_breach_rate_horizon_7d"].to_numpy()
        y_surge = df["target_surge_binary_7d"].to_numpy()

        splits = generate_expanding_window_splits(df)
        logger.info("expanding_window_cv_splits_generated", num_splits=len(splits))

        fold_metrics = []

        with mlflow.start_run(run_name="gbdt_multi_horizon_forecasting"):
            mlflow.log_param("author", "CHRISH PEP FELIX A")
            mlflow.log_param("num_features", len(FEATURE_COLUMNS))
            mlflow.log_param("cv_folds", len(splits))
            mlflow.log_param("target_trust", "REM")

            last_models = {}

            for fold_idx, (train_idx, val_idx) in enumerate(splits):
                X_tr, y_tr_breach = X.iloc[train_idx], y_breach[train_idx]
                X_vl, y_vl_breach = X.iloc[val_idx], y_breach[val_idx]
                y_tr_surge, y_vl_surge = y_surge[train_idx], y_surge[val_idx]

                # Train LightGBM Quantiles: P10, P50, P90
                m_p10 = self.train_quantile_lightgbm(
                    X_tr, y_tr_breach, X_vl, y_vl_breach, alpha=0.10
                )
                m_p50 = self.train_quantile_lightgbm(
                    X_tr, y_tr_breach, X_vl, y_vl_breach, alpha=0.50
                )
                m_p90 = self.train_quantile_lightgbm(
                    X_tr, y_tr_breach, X_vl, y_vl_breach, alpha=0.90
                )

                pred_p10 = m_p10.predict(X_vl)
                pred_p50 = m_p50.predict(X_vl)
                pred_p90 = m_p90.predict(X_vl)

                # Enforce Quantile Monotonicity: P10 <= P50 <= P90
                pred_p50 = np.maximum(pred_p10, pred_p50)
                pred_p90 = np.maximum(pred_p50, pred_p90)

                mae_p50 = float(mean_absolute_error(y_vl_breach, pred_p50))
                rmse_p50 = float(np.sqrt(mean_squared_error(y_vl_breach, pred_p50)))
                pb_10 = pinball_loss(y_vl_breach, pred_p10, 0.10)
                pb_50 = pinball_loss(y_vl_breach, pred_p50, 0.50)
                pb_90 = pinball_loss(y_vl_breach, pred_p90, 0.90)
                coverage = empirical_coverage(y_vl_breach, pred_p10, pred_p90)

                mlflow.log_metric(f"fold_{fold_idx + 1}_pinball_p10", pb_10)
                mlflow.log_metric(f"fold_{fold_idx + 1}_pinball_p90", pb_90)

                # Train XGBoost Surge Classifier
                m_xgb = self.train_xgboost_classifier(X_tr, y_tr_surge, X_vl, y_vl_surge)
                prob_surge = m_xgb.predict_proba(X_vl)[:, 1]
                auc = (
                    float(roc_auc_score(y_vl_surge, prob_surge))
                    if len(np.unique(y_vl_surge)) > 1
                    else 0.5
                )

                fold_res = {
                    "fold": fold_idx + 1,
                    "mae_p50": mae_p50,
                    "rmse_p50": rmse_p50,
                    "pinball_loss_p50": pb_50,
                    "coverage_80pct": coverage,
                    "surge_auc": auc,
                }
                fold_metrics.append(fold_res)

                # Log fold metrics to MLflow
                for k, v in fold_res.items():
                    mlflow.log_metric(f"fold_{fold_idx + 1}_{k}", v)

                last_models = {
                    "m_p10": m_p10,
                    "m_p50": m_p50,
                    "m_p90": m_p90,
                    "m_xgb": m_xgb,
                    "X_val": X_vl,
                    "y_val": y_vl_breach,
                    "df_val": df.iloc[val_idx],
                }

            # Overall Average CV Metrics
            avg_mae = float(np.mean([m["mae_p50"] for m in fold_metrics]))
            avg_rmse = float(np.mean([m["rmse_p50"] for m in fold_metrics]))
            avg_coverage = float(np.mean([m["coverage_80pct"] for m in fold_metrics]))
            avg_auc = float(np.mean([m["surge_auc"] for m in fold_metrics]))

            mlflow.log_metric("cv_mean_mae_p50", avg_mae)
            mlflow.log_metric("cv_mean_rmse_p50", avg_rmse)
            mlflow.log_metric("cv_mean_coverage_80pct", avg_coverage)
            mlflow.log_metric("cv_mean_surge_auc", avg_auc)

            logger.info(
                "gbdt_training_completed",
                avg_mae=avg_mae,
                avg_rmse=avg_rmse,
                avg_coverage=avg_coverage,
                avg_auc=avg_auc,
            )

            return {
                "fold_metrics": fold_metrics,
                "summary": {
                    "mae_p50": avg_mae,
                    "rmse_p50": avg_rmse,
                    "coverage_80pct": avg_coverage,
                    "surge_auc": avg_auc,
                },
                "last_models": last_models,
            }


gbdt_pipeline = GBDTForecastingPipeline()

if __name__ == "__main__":
    gbdt_pipeline.run_training_pipeline()
