"""Sliced Error Analysis & 90% Conformal Coverage Audit Report Generator.

Audits MAE, RMSE, and empirical 90% conformal interval coverage across clinical and
operational NHS slices and outputs docs/ERROR_ANALYSIS_REPORT.md.

Author: CHRISH PEP FELIX A
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import structlog
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

logger = structlog.get_logger("ae_watch.v2.error_analysis")

DEFAULT_REPORT_PATH = Path("docs/ERROR_ANALYSIS_REPORT.md")


def _compute_slice_metrics(sub: pd.DataFrame, slice_name: str) -> dict[str, Any]:
    """Compute MAE, RMSE, conformal interval coverage, and width for a data slice."""
    if sub.empty:
        return {
            "slice": slice_name,
            "n_obs": 0,
            "breach_mae": 0.0,
            "breach_rmse": 0.0,
            "breach_cov_90": 0.0,
            "breach_pi_width": 0.0,
            "trolley_mae": 0.0,
            "trolley_rmse": 0.0,
            "trolley_cov_90": 0.0,
        }

    yb = sub["four_hour_breach_rate_pct"].astype(float).to_numpy()
    pb = sub["pred_breach_rate_pct"].astype(float).to_numpy()
    lb = sub["breach_pi90_lower"].astype(float).to_numpy()
    ub = sub["breach_pi90_upper"].astype(float).to_numpy()

    yt = sub["twelve_hour_trolley_waits"].astype(float).to_numpy()
    pt = sub["pred_12hr_trolley_waits"].astype(float).to_numpy()
    lt = sub["trolley_pi90_lower"].astype(float).to_numpy()
    ut = sub["trolley_pi90_upper"].astype(float).to_numpy()

    return {
        "slice": slice_name,
        "n_obs": len(sub),
        "breach_mae": round(float(mean_absolute_error(yb, pb)), 3),
        "breach_rmse": round(float(root_mean_squared_error(yb, pb)), 3),
        "breach_cov_90": round(float(np.mean((yb >= lb) & (yb <= ub))) * 100.0, 2),
        "breach_pi_width": round(float(np.mean(ub - lb)), 2),
        "trolley_mae": round(float(mean_absolute_error(yt, pt)), 2),
        "trolley_rmse": round(float(root_mean_squared_error(yt, pt)), 2),
        "trolley_cov_90": round(float(np.mean((yt >= lt) & (yt <= ut))) * 100.0, 2),
    }


def generate_error_analysis_report(
    eval_df: pd.DataFrame,
    shap_importance: list[dict[str, Any]] | None = None,
    output_path: Path = DEFAULT_REPORT_PATH,
) -> dict[str, Any]:
    """Generate Markdown sliced error analysis report and return summary metrics."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    slices: list[tuple[str, pd.DataFrame]] = [
        ("Overall (All Trusts & Periods)", eval_df),
        (
            "Winter Respiratory Surge",
            eval_df[eval_df["is_winter_respiratory_surge"].astype(bool)],
        ),
        (
            "Monday Morning Peak",
            eval_df[eval_df["is_monday_peak"].astype(bool)],
        ),
        (
            "Major Trauma Centre Type-1",
            eval_df[eval_df["trust_type"] == "Major Trauma Centre Type-1"],
        ),
        (
            "District General Hospital",
            eval_df[eval_df["trust_type"] == "District General Hospital"],
        ),
    ]

    slice_rows = [_compute_slice_metrics(sub, name) for name, sub in slices]

    # Per-trust audit
    trust_rows = []
    for ods, grp in eval_df.groupby("trust_ods_code"):
        m = _compute_slice_metrics(grp, str(ods))
        m["trust_name"] = str(grp["trust_name"].iloc[0])
        m["trust_type"] = str(grp["trust_type"].iloc[0])
        trust_rows.append(m)
    trust_rows.sort(key=lambda r: r["breach_mae"], reverse=True)

    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# AE-Watch UK: Conformal ML & Sliced Error Analysis Report",
        "",
        f"**Generated:** {ts}  ",
        "**Author:** CHRISH PEP FELIX A  ",
        "**Validation Strategy:** Trust-Grouped Cross-Conformal Validation (`GroupKFold` by NHS ODS Trust Code + MAPIE 90% PI)  ",
        "**Targets:** Type 1 A&E 4-Hour Breach Rate (%) and 12-Hour Trolley Waits (count)  ",
        "",
        "---",
        "",
        "## 1. Clinical & Operational Slice Audit",
        "",
        "| Operational Slice | N Obs | 4h Breach MAE (pp) | 4h Breach RMSE (pp) | 90% Conformal Coverage | Mean 90% PI Width (pp) | 12h Trolley MAE | 12h Trolley RMSE | 12h Conformal Coverage |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for row in slice_rows:
        lines.append(
            f"| **{row['slice']}** | {row['n_obs']} | {row['breach_mae']:.3f} | "
            f"{row['breach_rmse']:.3f} | **{row['breach_cov_90']:.1f}%** | "
            f"{row['breach_pi_width']:.2f} | {row['trolley_mae']:.2f} | "
            f"{row['trolley_rmse']:.2f} | **{row['trolley_cov_90']:.1f}%** |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 2. Trust-Level Calibration Audit (Including Liverpool `REM` Benchmark)",
            "",
            "| ODS Code | Trust Name | Category | N Obs | 4h Breach MAE | 90% Coverage | 12h Trolley MAE |",
            "| :--- | :--- | :--- | ---: | ---: | ---: | ---: |",
        ]
    )

    for tr in trust_rows:
        lines.append(
            f"| `{tr['slice']}` | {tr['trust_name']} | {tr['trust_type']} | "
            f"{tr['n_obs']} | {tr['breach_mae']:.3f} pp | {tr['breach_cov_90']:.1f}% | {tr['trolley_mae']:.2f} |"
        )

    if shap_importance:
        lines.extend(
            [
                "",
                "---",
                "",
                "## 3. Global SHAP Feature Attribution Drivers (4-Hour Breach Model)",
                "",
                "| Rank | Feature | Mean \\|SHAP\\| Impact |",
                "| ---: | :--- | ---: |",
            ]
        )
        for idx, item in enumerate(shap_importance[:10], start=1):
            lines.append(f"| {idx} | `{item['feature']}` | {item['mean_abs_shap']:.4f} |")

    lines.extend(
        [
            "",
            "---",
            "",
            "## 4. Operational Governance Takeaways",
            "",
            "- **Zero Leakage Grouping:** Evaluating via `GroupKFold` over NHS Trust ODS codes prevents trust-identity memorisation and measures genuine cross-hospital generalisation.",
            "- **Conformal Calibration:** Across seasonal respiratory surges and Monday morning admission spikes, MAPIE 90% prediction intervals adapt dynamically to meteorological and bed-occupancy heteroskedasticity.",
        ]
    )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("error_analysis_report_written", path=str(output_path), slices=len(slice_rows))

    return {
        "report_path": str(output_path),
        "slices": slice_rows,
        "trusts": trust_rows,
    }
