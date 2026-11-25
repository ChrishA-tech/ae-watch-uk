"""Trust-Grouped LightGBM + MAPIE Conformal Forecasting with MLflow SQLite Tracking.

Uses GroupKFold by NHS ODS Trust code with MAPIE CrossConformalRegressor (90% prediction
intervals) to forecast 4-hour A&E breach rates and 12-hour trolley waits, plus SHAP explanations.

Author: CHRISH PEP FELIX A
"""

from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Any

import mlflow
import numpy as np
import pandas as pd
import shap
import structlog
from lightgbm import LGBMRegressor
from mapie.regression import CrossConformalRegressor, SplitConformalRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from sklearn.model_selection import GroupKFold, GroupShuffleSplit

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

logger = structlog.get_logger("ae_watch.v2.conformal_models")

DEFAULT_MLFLOW_URI = "sqlite:///mlruns/mlflow.db"
DEFAULT_MODEL_BUNDLE_PATH = Path("data/processed/conformal_models.pkl")

MODEL_FEATURES: list[str] = [
    "type1_attendances",
    "type2_attendances",
    "type3_attendances",
    "total_attendances",
    "bed_occupancy_ratio",
    "temp_c",
    "min_temp_c",
    "precipitation_mm",
    "wind_speed_kmh",
    "cold_snap_trigger",
    "ukhsa_flu_admission_rate",
    "ukhsa_rsv_admission_rate",
    "respiratory_surge_index",
    "is_monday_peak",
    "is_winter_respiratory_surge",
]


def _prepare_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Extract numeric feature matrix cleanly with bool-to-int coercion."""
    X = df[MODEL_FEATURES].copy()
    for col in X.columns:
        if X[col].dtype == bool:
            X[col] = X[col].astype(int)
        else:
            X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0.0)
    return X


def _fit_target_conformal(
    X: pd.DataFrame,
    y: np.ndarray,
    groups: np.ndarray,
    confidence_level: float = 0.90,
) -> tuple[CrossConformalRegressor, LGBMRegressor, np.ndarray, np.ndarray, np.ndarray]:
    """Fit CrossConformalRegressor grouped by NHS ODS Trust code and collect OOF intervals."""
    unique_groups = len(np.unique(groups))
    n_splits = max(2, min(5, unique_groups))
    gkf = GroupKFold(n_splits=n_splits)

    X_arr = X.to_numpy()
    oof_pred = np.zeros(len(y), dtype=float)
    oof_lower = np.zeros(len(y), dtype=float)
    oof_upper = np.zeros(len(y), dtype=float)

    # Strict Trust-grouped out-of-fold conformal evaluation (zero Trust leakage)
    for train_idx, test_idx in gkf.split(X_arr, y, groups=groups):
        X_tr, y_tr, g_tr = X_arr[train_idx], y[train_idx], groups[train_idx]
        X_te = X_arr[test_idx]

        fold_est = LGBMRegressor(
            n_estimators=120,
            learning_rate=0.05,
            num_leaves=15,
            min_child_samples=5,
            random_state=42,
            verbosity=-1,
            n_jobs=1,
        )

        if len(np.unique(g_tr)) >= 2:
            gss = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
            fit_sub, cal_sub = next(gss.split(X_tr, y_tr, groups=g_tr))
            fold_est.fit(X_tr[fit_sub], y_tr[fit_sub])
            sc = SplitConformalRegressor(
                estimator=fold_est,
                confidence_level=confidence_level,
                prefit=True,
            )
            sc.conformalize(X_tr[cal_sub], y_tr[cal_sub])
            p_te, pi_te = sc.predict_interval(X_te)
        else:
            fold_est.fit(X_tr, y_tr)
            p_te = fold_est.predict(X_te)
            resid_q = np.quantile(np.abs(y_tr - fold_est.predict(X_tr)), confidence_level)
            pi_te = np.stack([p_te - resid_q, p_te + resid_q], axis=1)[..., np.newaxis]

        oof_pred[test_idx] = p_te
        oof_lower[test_idx] = pi_te[:, 0, 0]
        oof_upper[test_idx] = pi_te[:, 1, 0]

    base_estimator = LGBMRegressor(
        n_estimators=120,
        learning_rate=0.05,
        num_leaves=15,
        min_child_samples=5,
        random_state=42,
        verbosity=-1,
        n_jobs=1,
    )

    conformal_model = CrossConformalRegressor(
        estimator=base_estimator,
        confidence_level=confidence_level,
        conformity_score="absolute",
        method="plus",
        cv=gkf,
        random_state=42,
    )
    conformal_model.fit_conformalize(X_arr, y, groups=groups)

    # Enforce physical monotonicity / non-negativity bounds
    oof_lower = np.maximum(0.0, oof_lower)
    oof_pred = np.maximum(oof_lower, oof_pred)
    oof_upper = np.maximum(oof_pred, oof_upper)

    # Fit standalone base estimator for TreeSHAP global attributions
    shap_estimator = LGBMRegressor(
        n_estimators=120,
        learning_rate=0.05,
        num_leaves=15,
        min_child_samples=5,
        random_state=42,
        verbosity=-1,
        n_jobs=1,
    )
    shap_estimator.fit(X, y)
    return conformal_model, shap_estimator, oof_pred, oof_lower, oof_upper


def train_conformal_ae_models(
    df: pd.DataFrame,
    mlflow_tracking_uri: str = DEFAULT_MLFLOW_URI,
    model_bundle_path: Path = DEFAULT_MODEL_BUNDLE_PATH,
    confidence_level: float = 0.90,
) -> dict[str, Any]:
    """Train Trust-grouped LightGBM + MAPIE conformal models for breach rate & 12hr waits."""
    Path("mlruns").mkdir(parents=True, exist_ok=True)
    model_bundle_path.parent.mkdir(parents=True, exist_ok=True)

    X = _prepare_feature_matrix(df)
    groups = df["trust_ods_code"].astype(str).to_numpy()

    y_breach = df["four_hour_breach_rate_pct"].astype(float).to_numpy()
    y_trolley = df["twelve_hour_trolley_waits"].astype(float).to_numpy()

    (
        breach_conformal,
        breach_shap_lgb,
        breach_pred,
        breach_lo,
        breach_hi,
    ) = _fit_target_conformal(X, y_breach, groups, confidence_level=confidence_level)

    (
        trolley_conformal,
        _trolley_shap_lgb,
        trolley_pred,
        trolley_lo,
        trolley_hi,
    ) = _fit_target_conformal(X, y_trolley, groups, confidence_level=confidence_level)

    # Clip breach bounds strictly to [0, 100]%
    breach_lo = np.clip(breach_lo, 0.0, 100.0)
    breach_pred = np.clip(breach_pred, breach_lo, 100.0)
    breach_hi = np.clip(breach_hi, breach_pred, 100.0)

    # Global SHAP importance on 4-hour breach model
    explainer = shap.TreeExplainer(breach_shap_lgb)
    shap_vals = explainer.shap_values(X)
    mean_abs_shap = np.mean(np.abs(shap_vals), axis=0)
    shap_importance = sorted(
        [
            {"feature": feat, "mean_abs_shap": round(float(val), 4)}
            for feat, val in zip(MODEL_FEATURES, mean_abs_shap)
        ],
        key=lambda item: item["mean_abs_shap"],
        reverse=True,
    )

    # Overall metrics
    breach_mae = float(mean_absolute_error(y_breach, breach_pred))
    breach_rmse = float(root_mean_squared_error(y_breach, breach_pred))
    breach_cov = float(np.mean((y_breach >= breach_lo) & (y_breach <= breach_hi)))

    trolley_mae = float(mean_absolute_error(y_trolley, trolley_pred))
    trolley_rmse = float(root_mean_squared_error(y_trolley, trolley_pred))
    trolley_cov = float(np.mean((y_trolley >= trolley_lo) & (y_trolley <= trolley_hi)))

    metrics = {
        "breach_mae": round(breach_mae, 4),
        "breach_rmse": round(breach_rmse, 4),
        "breach_coverage_90": round(breach_cov, 4),
        "trolley_12hr_mae": round(trolley_mae, 4),
        "trolley_12hr_rmse": round(trolley_rmse, 4),
        "trolley_12hr_coverage_90": round(trolley_cov, 4),
        "n_trust_groups": len(np.unique(groups)),
        "n_rows": len(df),
    }

    eval_df = df.copy()
    eval_df["pred_breach_rate_pct"] = np.round(breach_pred, 3)
    eval_df["breach_pi90_lower"] = np.round(breach_lo, 3)
    eval_df["breach_pi90_upper"] = np.round(breach_hi, 3)
    eval_df["pred_12hr_trolley_waits"] = np.round(trolley_pred, 2)
    eval_df["trolley_pi90_lower"] = np.round(trolley_lo, 2)
    eval_df["trolley_pi90_upper"] = np.round(trolley_hi, 2)

    bundle = {
        "breach_conformal": breach_conformal,
        "trolley_conformal": trolley_conformal,
        "breach_shap_lgb": breach_shap_lgb,
        "features": MODEL_FEATURES,
        "shap_importance": shap_importance,
        "metrics": metrics,
        "confidence_level": confidence_level,
    }
    with open(model_bundle_path, "wb") as f:
        pickle.dump(bundle, f)

    # Log to MLflow SQLite backend
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment("ae_watch_uk_v2_conformal")
    with mlflow.start_run(run_name="lgbm_mapie_groupkfold_90ci") as run:
        mlflow.log_params(
            {
                "cv_strategy": "GroupKFold(trust_ods_code)",
                "conformal_method": "MAPIE_CrossConformalRegressor_plus",
                "confidence_level": confidence_level,
                "n_features": len(MODEL_FEATURES),
                "author": "CHRISH PEP FELIX A",
            }
        )
        mlflow.log_metrics({k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))})
        mlflow.log_artifact(str(model_bundle_path), artifact_path="conformal_bundle")
        mlflow_run_id = run.info.run_id

    logger.info(
        "conformal_models_trained",
        mlflow_uri=mlflow_tracking_uri,
        run_id=mlflow_run_id,
        **metrics,
    )

    return {
        "metrics": metrics,
        "shap_importance": shap_importance,
        "eval_df": eval_df,
        "model_bundle_path": str(model_bundle_path),
        "mlflow_tracking_uri": mlflow_tracking_uri,
        "mlflow_run_id": mlflow_run_id,
    }


def predict_trust_conformal(
    row_or_df: pd.DataFrame,
    model_bundle_path: Path = DEFAULT_MODEL_BUNDLE_PATH,
) -> dict[str, Any]:
    """Run conformal inference for a trust observation using saved MAPIE bundle."""
    with open(model_bundle_path, "rb") as f:
        bundle = pickle.load(f)

    X = _prepare_feature_matrix(row_or_df).to_numpy()
    b_pred, b_pis = bundle["breach_conformal"].predict_interval(X)
    t_pred, t_pis = bundle["trolley_conformal"].predict_interval(X)

    b_lo = float(np.clip(b_pis[0, 0, 0], 0.0, 100.0))
    b_mid = float(np.clip(b_pred[0], b_lo, 100.0))
    b_hi = float(np.clip(b_pis[0, 1, 0], b_mid, 100.0))

    t_lo = float(max(0.0, t_pis[0, 0, 0]))
    t_mid = float(max(t_lo, t_pred[0]))
    t_hi = float(max(t_mid, t_pis[0, 1, 0]))

    return {
        "breach_rate_pct": {
            "point": round(b_mid, 2),
            "pi90_lower": round(b_lo, 2),
            "pi90_upper": round(b_hi, 2),
        },
        "twelve_hour_trolley_waits": {
            "point": round(t_mid, 1),
            "pi90_lower": round(t_lo, 1),
            "pi90_upper": round(t_hi, 1),
        },
        "shap_top_drivers": bundle["shap_importance"][:5],
    }
