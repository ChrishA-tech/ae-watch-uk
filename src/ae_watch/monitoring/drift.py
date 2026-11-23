"""Data & Concept Drift Monitoring for AE-Watch UK.

Computes Population Stability Index (PSI), Kolmogorov-Smirnov (KS) test statistics,
and feature distribution drift comparing baseline winter (2023-2024)
against incoming 2025-2026 winter periods using Evidently AI and SciPy.
Author: CHRISH PEP FELIX A
"""

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from ae_watch.models.train_gbdt import load_dataset_from_db
from ae_watch.utils.logger import logger

DRIFT_FEATURE_COLUMNS = [
    "breach_4hr_pct",
    "total_cold_snap_degree_days",
    "flu_admission_rate",
    "covid_positivity_pct",
    "idw_neighbor_breach_rate",
    "monthly_avg_temp_c",
]


def calculate_psi(expected: np.ndarray, actual: np.ndarray, num_buckets: int = 10) -> float:
    """Calculate the Population Stability Index (PSI) between reference and current distributions.

    PSI < 0.1: No significant change / stable
    0.1 <= PSI < 0.2: Moderate drift detected
    PSI >= 0.2: Significant feature distribution shift
    """
    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    # Determine percentile cutoffs from baseline reference
    percentiles = np.linspace(0, 100, num_buckets + 1)
    quantiles = np.percentile(expected, percentiles)
    quantiles[0] = -np.inf
    quantiles[-1] = np.inf

    # Bucket counts
    expected_counts, _ = np.histogram(expected, bins=quantiles)
    actual_counts, _ = np.histogram(actual, bins=quantiles)

    # Fractions with Laplace smoothing
    expected_frac = (expected_counts + 1e-4) / (len(expected) + 1e-4 * num_buckets)
    actual_frac = (actual_counts + 1e-4) / (len(actual) + 1e-4 * num_buckets)

    psi_val = np.sum((actual_frac - expected_frac) * np.log(actual_frac / expected_frac))
    return float(max(0.0, psi_val))


class WinterPressureDriftMonitor:
    """Detects epidemiological and operational drift across winter seasons."""

    def __init__(
        self,
        psi_threshold: float = 0.2,
        alpha: float = 0.05,
        features: list[str] | None = None,
    ):
        self.psi_threshold = psi_threshold
        self.alpha = alpha
        self.features = features or DRIFT_FEATURE_COLUMNS

    def split_reference_and_current(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Split dataset into reference baseline (<= 2024) and current monitoring window (> 2024)."""
        sorted_periods = sorted(df["period_date"].unique())
        midpoint = len(sorted_periods) // 2
        ref_periods = set(sorted_periods[:midpoint])
        curr_periods = set(sorted_periods[midpoint:])

        df_ref = df[df["period_date"].isin(ref_periods)].copy()
        df_curr = df[df["period_date"].isin(curr_periods)].copy()

        logger.info(
            "drift_dataset_split",
            reference_rows=len(df_ref),
            current_rows=len(df_curr),
            ref_periods=len(ref_periods),
            curr_periods=len(curr_periods),
        )
        return df_ref, df_curr

    def detect_feature_drift(self, df_ref: pd.DataFrame, df_curr: pd.DataFrame) -> dict[str, Any]:
        """Execute PSI and KS-test distribution drift checks per feature."""
        feature_metrics: dict[str, Any] = {}
        drifted_features = []

        for col in self.features:
            if col not in df_ref.columns or col not in df_curr.columns:
                continue

            v_ref = df_ref[col].dropna().to_numpy(dtype=float)
            v_curr = df_curr[col].dropna().to_numpy(dtype=float)

            psi_score = calculate_psi(v_ref, v_curr)
            ks_res = ks_2samp(v_ref, v_curr)
            ks_stat = float(ks_res.statistic)
            p_val = float(ks_res.pvalue)

            has_drift = psi_score >= self.psi_threshold or p_val < self.alpha
            if has_drift:
                drifted_features.append(col)

            feature_metrics[col] = {
                "psi_score": round(psi_score, 4),
                "ks_statistic": round(ks_stat, 4),
                "p_value": round(p_val, 5),
                "has_drift": has_drift,
                "ref_mean": round(float(np.mean(v_ref)), 3),
                "curr_mean": round(float(np.mean(v_curr)), 3),
                "ref_std": round(float(np.std(v_ref)), 3),
                "curr_std": round(float(np.std(v_curr)), 3),
            }

        dataset_drift_detected = len(drifted_features) > (len(self.features) / 2)

        summary = {
            "dataset_drift_detected": dataset_drift_detected,
            "drifted_features_count": len(drifted_features),
            "total_features_monitored": len(self.features),
            "drifted_features": drifted_features,
            "feature_details": feature_metrics,
        }

        logger.info(
            "drift_monitoring_completed",
            dataset_drift=dataset_drift_detected,
            drifted_count=len(drifted_features),
            drifted_features=drifted_features,
        )

        return summary

    def run(self) -> dict[str, Any]:
        """Execute full drift monitoring workflow."""
        df = load_dataset_from_db()
        df_ref, df_curr = self.split_reference_and_current(df)
        return self.detect_feature_drift(df_ref, df_curr)


drift_monitor = WinterPressureDriftMonitor()

if __name__ == "__main__":
    res = drift_monitor.run()
    print("Dataset drift detected:", res["dataset_drift_detected"])
    print("Drifted features:", res["drifted_features"])
