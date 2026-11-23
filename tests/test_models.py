"""Unit and integration tests for multi-horizon forecasting models and explainability.

Author: CHRISH PEP FELIX A
Project: AE-Watch UK
"""

import numpy as np
import pandas as pd
import torch

from ae_watch.models.train_gbdt import (
    GBDTForecastingPipeline,
    empirical_coverage,
    generate_expanding_window_splits,
    pinball_loss,
)
from ae_watch.models.train_tft import (
    TemporalFusionNetwork,
    get_optimal_torch_device,
)


def test_expanding_window_splits_zero_leakage():
    """Verify that generate_expanding_window_splits never includes future data in training sets."""
    # 20 distinct consecutive months
    periods = [f"2024-{m:02d}-01" for m in range(1, 13)] + [f"2025-{m:02d}-01" for m in range(1, 9)]
    df = pd.DataFrame(
        {
            "period_date": np.repeat(periods, 5),
            "feature_1": np.random.randn(100),
            "target": np.random.randn(100),
        }
    )

    splits = generate_expanding_window_splits(df, min_train_periods=8, val_step=3)
    assert len(splits) >= 2

    prev_train_len = 0
    for i, (train_idx, val_idx) in enumerate(splits):
        # 1. No overlap between train and validation indices
        assert len(set(train_idx).intersection(set(val_idx))) == 0

        # 2. Expanding window property: train size strictly increases
        assert len(train_idx) > prev_train_len
        prev_train_len = len(train_idx)

        # 3. Zero temporal leakage: maximum training date < minimum validation date
        train_dates = pd.to_datetime(df.iloc[train_idx]["period_date"])
        val_dates = pd.to_datetime(df.iloc[val_idx]["period_date"])
        assert train_dates.max() < val_dates.min(), f"Split {i} leaked future data into train!"


def test_pinball_loss_and_empirical_coverage():
    """Verify pinball loss and 80% empirical interval coverage calculation."""
    y_true = np.array([20.0, 25.0, 30.0, 35.0])
    y_p10 = np.array([18.0, 22.0, 27.0, 31.0])
    y_p90 = np.array([22.0, 28.0, 33.0, 38.0])

    loss_10 = pinball_loss(y_true, y_p10, 0.10)
    loss_90 = pinball_loss(y_true, y_p90, 0.90)
    assert loss_10 >= 0.0
    assert loss_90 >= 0.0

    cov = empirical_coverage(y_true, y_p10, y_p90)
    # All 4 points are within [p10, p90], so coverage should be 1.0 (100%)
    assert cov == 1.0


def test_quantile_monotonicity_lightgbm():
    """Verify LightGBM quantile models preserve P10 <= P50 <= P90 intervals."""
    np.random.seed(42)
    n_samples = 120
    X = pd.DataFrame(
        {
            "breach_rate_lag_1m": np.random.uniform(15.0, 45.0, n_samples),
            "flu_admission_rate": np.random.uniform(0.5, 20.0, n_samples),
            "total_cold_snap_degree_days": np.random.uniform(0.0, 50.0, n_samples),
            "idw_neighbor_breach_rate": np.random.uniform(15.0, 45.0, n_samples),
        }
    )
    y = (
        X["breach_rate_lag_1m"] * 0.8
        + X["flu_admission_rate"] * 0.5
        + np.random.normal(0, 2, n_samples)
    )

    pipeline = GBDTForecastingPipeline(tracking_uri="file:./mlruns")
    models = {}
    for alpha in [0.10, 0.50, 0.90]:
        models[alpha] = pipeline.train_quantile_lightgbm(
            X_train=X, y_train=y.to_numpy(), X_val=X, y_val=y.to_numpy(), alpha=alpha
        )

    p10 = models[0.10].predict(X)
    p50 = models[0.50].predict(X)
    p90 = models[0.90].predict(X)

    # Average predictions must respect monotonic ordering
    assert np.mean(p10) <= np.mean(p50) <= np.mean(p90)
    mean_interval_width = np.mean(p90 - p10)
    assert mean_interval_width > 0.0


def test_pytorch_device_selection_and_tft_forward():
    """Verify PyTorch device fallback and TFT forward pass execution."""
    device = get_optimal_torch_device()
    assert isinstance(device, torch.device)
    assert device.type in ["mps", "cpu", "cuda"]

    model = TemporalFusionNetwork(
        input_dim=8,
        hidden_dim=16,
        num_heads=2,
        num_quantiles=3,
    ).to(device)

    dummy_input = torch.randn(4, 6, 8, device=device)
    output = model(dummy_input)

    assert output.shape == (4, 3)
    assert not torch.isnan(output).any()
    assert not torch.isinf(output).any()
