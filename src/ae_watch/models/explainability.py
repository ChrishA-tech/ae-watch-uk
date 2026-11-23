"""Model Explainability and TreeSHAP Attribution for AE-Watch UK.

Generates global feature attributions and localized Liverpool University Hospitals (REM)
TreeSHAP breakdowns, isolating cold-snap degree days, neighbor catchment spillover,
and epidemiological surge drivers.
Author: CHRISH PEP FELIX A
"""

from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
import shap

from ae_watch.models.train_gbdt import FEATURE_COLUMNS, load_dataset_from_db
from ae_watch.utils.logger import logger


class ModelExplainer:
    """Computes TreeSHAP feature importance and local instance attributions."""

    def __init__(self, model: lgb.LGBMRegressor | None = None):
        self.model = model
        self.feature_names = FEATURE_COLUMNS

    def fit_explainer(self, model: lgb.LGBMRegressor) -> shap.TreeExplainer:
        """Create and fit TreeExplainer for LightGBM model."""
        self.model = model
        return shap.TreeExplainer(model)

    def explain_global(self, explainer: shap.TreeExplainer, X: pd.DataFrame) -> dict[str, float]:
        """Compute mean absolute SHAP values across all features."""
        logger.info("computing_global_shap_attributions", samples=len(X))
        shap_values = explainer.shap_values(X)
        mean_abs_shap = np.mean(np.abs(shap_values), axis=0)

        importance_dict = {
            feat: round(float(val), 4) for feat, val in zip(self.feature_names, mean_abs_shap)
        }
        # Sort descending by importance
        sorted_importance = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
        return sorted_importance

    def explain_liverpool_rem(
        self,
        explainer: shap.TreeExplainer,
        df: pd.DataFrame,
    ) -> dict[str, Any]:
        """Extract local SHAP feature breakdown for Liverpool University Hospitals (REM) during winter surge."""
        rem_rows = df[df["trust_code"] == "REM"].sort_values("period_date", ascending=False)
        if rem_rows.empty:
            logger.warning("no_rem_rows_found_for_shap")
            return {}

        # Select latest winter peak row (or most recent available)
        rem_instance = rem_rows.iloc[0]
        X_inst = rem_rows[FEATURE_COLUMNS].iloc[0:1].fillna(0.0)

        shap_values = explainer.shap_values(X_inst)
        expected_value = float(explainer.expected_value)
        predicted_val = float(self.model.predict(X_inst)[0]) if self.model else expected_value

        inst_shap = shap_values[0]

        contributions = {
            feat: {
                "feature_value": float(X_inst[feat].iloc[0]),
                "shap_impact": round(float(inst_shap[i]), 4),
            }
            for i, feat in enumerate(FEATURE_COLUMNS)
        }

        # Sort top positive and negative drivers
        top_positive_drivers = sorted(
            [(k, v["shap_impact"]) for k, v in contributions.items() if v["shap_impact"] > 0],
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        top_mitigating_drivers = sorted(
            [(k, v["shap_impact"]) for k, v in contributions.items() if v["shap_impact"] < 0],
            key=lambda x: x[1],
        )[:5]

        logger.info(
            "rem_shap_breakdown_computed",
            period=str(rem_instance["period_date"]),
            predicted_breach_rate=predicted_val,
            base_value=expected_value,
            top_drivers=top_positive_drivers,
        )

        return {
            "period_date": str(rem_instance["period_date"]),
            "trust_code": "REM",
            "trust_name": "Liverpool University Hospitals NHS Foundation Trust",
            "predicted_breach_rate": round(predicted_val, 2),
            "base_value": round(expected_value, 2),
            "top_positive_drivers": top_positive_drivers,
            "top_mitigating_drivers": top_mitigating_drivers,
            "all_contributions": contributions,
        }

    def run_explainability_pipeline(self) -> dict[str, Any]:
        """Train baseline LightGBM model and generate global and Liverpool REM SHAP explanations."""
        df = load_dataset_from_db()
        X = df[FEATURE_COLUMNS].fillna(0.0)
        y = df["target_breach_rate_horizon_7d"].to_numpy()

        model = lgb.LGBMRegressor(
            n_estimators=100, learning_rate=0.05, random_state=42, verbosity=-1
        )
        model.fit(X, y)

        explainer = self.fit_explainer(model)
        global_imp = self.explain_global(explainer, X)
        rem_explanation = self.explain_liverpool_rem(explainer, df)

        return {
            "global_importance": global_imp,
            "liverpool_rem_explanation": rem_explanation,
        }


model_explainer = ModelExplainer()

if __name__ == "__main__":
    model_explainer.run_explainability_pipeline()
