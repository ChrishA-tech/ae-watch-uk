"""Unit and integration tests for data and prediction drift monitoring.

Author: CHRISH PEP FELIX A
Project: AE-Watch UK
"""

import numpy as np
import pandas as pd

from ae_watch.monitoring.drift import (
    WinterPressureDriftMonitor,
    calculate_psi,
)


def test_psi_identical_distributions():
    """Verify PSI between identical distributions is essentially zero (< 0.05)."""
    np.random.seed(42)
    ref = np.random.normal(loc=30.0, scale=5.0, size=1000)
    curr = np.random.normal(loc=30.0, scale=5.0, size=1000)

    psi = calculate_psi(ref, curr, num_buckets=10)
    assert psi < 0.05, f"Expected near-zero PSI, got {psi:.4f}"


def test_psi_shifted_distributions():
    """Verify PSI detects significant distribution shift (PSI > 0.20)."""
    np.random.seed(42)
    ref = np.random.normal(loc=20.0, scale=3.0, size=1000)
    # Substantial distribution shift: mean shifted by +15 units
    curr = np.random.normal(loc=35.0, scale=4.0, size=1000)

    psi = calculate_psi(ref, curr, num_buckets=10)
    assert psi > 0.20, f"Expected significant PSI (>0.20), got {psi:.4f}"


def test_drift_monitor_synthetic_workflow():
    """Verify WinterPressureDriftMonitor correctly flags drifted features and generates report."""
    np.random.seed(42)
    n = 200

    features = [
        "breach_4hr_pct",
        "total_cold_snap_degree_days",
        "flu_admission_rate",
    ]

    ref_df = pd.DataFrame(
        {
            "breach_4hr_pct": np.random.normal(25.0, 3.0, n),
            "total_cold_snap_degree_days": np.random.exponential(10.0, n),
            "flu_admission_rate": np.random.normal(5.0, 1.0, n),
        }
    )

    # Shift flu_admission_rate dramatically in current
    curr_df = pd.DataFrame(
        {
            "breach_4hr_pct": np.random.normal(25.0, 3.0, n),  # stable
            "total_cold_snap_degree_days": np.random.exponential(10.0, n),  # stable
            "flu_admission_rate": np.random.normal(25.0, 5.0, n),  # drifted!
        }
    )

    monitor = WinterPressureDriftMonitor(features=features, psi_threshold=0.20)
    report = monitor.detect_feature_drift(ref_df, curr_df)

    assert "dataset_drift_detected" in report
    assert "feature_details" in report
    assert "flu_admission_rate" in report["feature_details"]

    flu_metric = report["feature_details"]["flu_admission_rate"]
    assert flu_metric["has_drift"] is True
    assert flu_metric["psi_score"] > 0.20

    breach_metric = report["feature_details"]["breach_4hr_pct"]
    assert breach_metric["has_drift"] is False
