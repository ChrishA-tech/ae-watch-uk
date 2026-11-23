"""Unit and integration tests for spatial and temporal feature engineering.

Author: CHRISH PEP FELIX A
Project: AE-Watch UK
"""

from datetime import date

import h3
import polars as pl

from ae_watch.features.spatial import (
    compute_idw_catchment_spillover,
    compute_trust_distance_matrix,
    get_trust_h3_index,
    haversine_distance_km,
)
from ae_watch.features.temporal import (
    FeaturePipeline,
    get_bank_holidays_in_month,
)


def test_haversine_distance():
    """Verify Haversine distance matches known geographic distances."""
    # Liverpool Royal (53.407, -2.958) to Countess of Chester (53.210, -2.899) is ~22 km
    dist = haversine_distance_km(53.4093, -2.9566, 53.2104, -2.8986)
    assert 20.0 <= dist <= 25.0

    # Same point distance is 0.0
    assert haversine_distance_km(53.4093, -2.9566, 53.4093, -2.9566) == 0.0


def test_h3_resolution_7_assignment():
    """Verify H3 resolution 7 spatial indexing for Liverpool REM coordinates."""
    cell = get_trust_h3_index("REM", resolution=7)
    assert isinstance(cell, str)
    assert h3.get_resolution(cell) == 7

    # Verify fallback for unknown trust works gracefully
    fallback_cell = get_trust_h3_index("UNKNOWN_TRUST", resolution=7)
    assert fallback_cell == cell


def test_trust_distance_matrix():
    """Verify pairwise distance matrix construction across Cheshire & Merseyside trusts."""
    dist_matrix = compute_trust_distance_matrix()
    assert ("REM", "REM") in dist_matrix
    assert dist_matrix[("REM", "REM")] == 0.0
    assert ("REM", "RBL") in dist_matrix
    assert dist_matrix[("REM", "RBL")] > 0.0
    # Symmetric property
    assert dist_matrix[("REM", "RBL")] == dist_matrix[("RBL", "REM")]


def test_spatial_idw_catchment_spillover():
    """Verify Inverse Distance Weighting calculations for neighboring trusts around Liverpool REM."""
    # Mock data spanning 2 periods across trusts
    dates = [date(2024, 1, 1), date(2024, 2, 1)]
    records = []
    for d in dates:
        records.extend(
            [
                {
                    "period_date": d,
                    "trust_code": "REM",
                    "breach_4hr_pct": 30.0,
                    "total_attendances": 15000.0,
                },
                {
                    "period_date": d,
                    "trust_code": "RBL",
                    "breach_4hr_pct": 40.0,
                    "total_attendances": 8000.0,
                },
                {
                    "period_date": d,
                    "trust_code": "RBS",
                    "breach_4hr_pct": 20.0,
                    "total_attendances": 5000.0,
                },
            ]
        )

    df = pl.DataFrame(records)
    spillover_df = compute_idw_catchment_spillover(df, target_trust="REM", radius_km=25.0)

    assert len(spillover_df) == 2
    assert "idw_neighbor_breach_rate" in spillover_df.columns
    assert "idw_neighbor_attendance_pressure" in spillover_df.columns

    for row in spillover_df.iter_rows(named=True):
        # Neighbor breach must be a weighted average between 20.0 and 40.0
        assert 20.0 <= row["idw_neighbor_breach_rate"] <= 40.0
        assert row["active_neighbors_count"] >= 1


def test_temporal_feature_engineering_pipeline():
    """Verify bank holiday counting, calendar encodings, and autoregressive lag logic."""
    # Bank holidays in January (New Year's Day)
    assert get_bank_holidays_in_month(2024, 1) >= 1
    # Bank holidays in December (Christmas + Boxing Day)
    assert get_bank_holidays_in_month(2024, 12) >= 2

    # Create synthetic multi-period dataframe
    pipeline = FeaturePipeline()
    dates = [
        date(2024, 1, 1),
        date(2024, 2, 1),
        date(2024, 3, 1),
        date(2024, 4, 1),
        date(2024, 5, 1),
    ]

    records = []
    for d in dates:
        records.append(
            {
                "period_date": d,
                "trust_code": "REM",
                "trust_name": "Liverpool University Hospitals NHS Foundation Trust",
                "type1_attendances": 10000.0,
                "type1_over4hr": 3000.0,
                "total_attendances": 15000.0,
                "total_over4hr": 4500.0,
                "breach_4hr_pct": 30.0,
                "performance_4hr_pct": 70.0,
                "monthly_avg_temp_c": 5.0,
                "monthly_min_temp_c": 0.0,
                "monthly_min_apparent_temp_c": -2.0,
                "total_frost_days": 4,
                "total_cold_snap_degree_days": 15.0,
                "total_precipitation_mm": 50.0,
                "max_wind_speed_kmh": 30.0,
                "flu_admission_rate": 3.0,
                "flu_positivity_pct": 5.0,
                "flu_admission_rate_lag_2w": 2.0,
                "rsv_admission_rate": 1.0,
                "rsv_positivity_pct": 2.0,
                "norovirus_total_cases": 10,
                "covid_positivity_pct": 4.0,
                "covid_admission_rate": 2.0,
                "nhs111_resp_calls_7d_avg": 200.0,
                "is_cheshire_merseyside": 1,
                "is_target_benchmark_trust": 1,
            }
        )

    raw_df = pl.DataFrame(records)
    featured = pipeline.engineer_features(raw_df)

    assert "sin_month" in featured.columns
    assert "cos_month" in featured.columns
    assert "bank_holiday_count" in featured.columns
    assert "breach_rate_lag_1m" in featured.columns
    assert "target_breach_rate_horizon_7d" in featured.columns
    assert "target_surge_binary_7d" in featured.columns

    # Verify no NaN values in required features
    for col in ["sin_month", "cos_month", "breach_rate_lag_1m", "breach_rolling_3m_mean"]:
        assert featured[col].null_count() == 0
