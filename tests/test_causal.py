"""Unit and integration tests for causal inference models (DoWhy Difference-in-Differences).

Author: CHRISH PEP FELIX A
Project: AE-Watch UK
"""

import numpy as np
import pandas as pd
import pytest

from ae_watch.causal.did import ColdHealthAlertCausalEstimator


def test_did_causal_estimator_synthetic_experiment():
    """Verify DiD estimator recovers known positive treatment effect in controlled setting."""
    np.random.seed(42)

    # Simulate 10 trusts over 40 months
    trusts = [f"TRUST_{i}" for i in range(10)]
    periods = [f"2024-{m:02d}-01" for m in range(1, 13)] + [
        f"2025-{m:02d}-01" for m in range(1, 13)
    ]

    records = []
    for t in trusts:
        trust_base = np.random.uniform(20.0, 35.0)
        for p in periods:
            month = int(p.split("-")[1])
            is_winter = month in [11, 12, 1, 2]
            cold_degree_days = (
                np.random.uniform(25.0, 45.0) if is_winter else np.random.uniform(0.0, 5.0)
            )
            records.append(
                {
                    "trust_code": t,
                    "period_date": p,
                    "total_cold_snap_degree_days": cold_degree_days,
                    "base_breach": trust_base,
                }
            )

    df = pd.DataFrame(records)

    # Treatment: cold_snap_degree_days >= 20.0
    treatment = (df["total_cold_snap_degree_days"] >= 20.0).astype(int)
    # True causal effect of cold alert = +3.5 percentage points breach
    true_effect = 3.5
    df["breach_4hr_pct"] = (
        df["base_breach"] + true_effect * treatment + np.random.normal(0, 1.0, len(df))
    )

    estimator = ColdHealthAlertCausalEstimator(cold_degree_days_threshold=20.0)
    result = estimator.estimate_causal_effect(df)

    # Estimated effect should be positive and close to true_effect (3.5)
    point_est = result["point_estimate_breach_pct_increase"]
    assert 2.0 <= point_est <= 5.0
    assert result["is_statistically_significant"] is True
    assert result["p_value"] < 0.05
    assert result["refutation_test_passed"] is True


def test_did_causal_estimator_handles_missing_columns():
    """Verify that ColdHealthAlertCausalEstimator raises clear ValueError when required columns missing."""
    estimator = ColdHealthAlertCausalEstimator()
    bad_df = pd.DataFrame({"some_other_column": [1, 2, 3]})

    with pytest.raises(ValueError, match="Missing required columns"):
        estimator.estimate_causal_effect(bad_df)
