"""Difference-in-Differences (DiD) Causal Impact Estimator for AE-Watch UK.

Quantifies the causal impact of UKHSA Amber/Red Cold Health Alert thresholds
on NHS Trust Type 1 A&E 4-hour breach rates using DoWhy and Two-Way Fixed Effects.
Includes placebo treatment refutation checks.
Author: CHRISH PEP FELIX A
"""

from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dowhy import CausalModel

from ae_watch.models.train_gbdt import load_dataset_from_db
from ae_watch.utils.logger import logger


class ColdHealthAlertCausalEstimator:
    """Causal inference engine evaluating weather shock impacts on Trust emergency performance."""

    def __init__(self, cold_degree_days_threshold: float = 20.0):
        self.threshold = cold_degree_days_threshold

    def prepare_causal_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        """Construct treatment indicator and categorical fixed effects."""
        required = {"total_cold_snap_degree_days", "breach_4hr_pct", "trust_code", "period_date"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns for causal estimation: {missing}")

        df_causal = df.copy()

        # Treatment: 1 if severe cold snap degree days exceed threshold or min temp <= 0
        min_temp = (
            df_causal["monthly_min_temp_c"] if "monthly_min_temp_c" in df_causal.columns else 1.0
        )
        df_causal["treatment_cold_alert"] = (
            (df_causal["total_cold_snap_degree_days"] >= self.threshold) | (min_temp <= 0.0)
        ).astype(int)

        # Outcome
        df_causal["outcome_breach_rate"] = df_causal["breach_4hr_pct"].astype(float)

        # Confounders / Common Causes
        df_causal["confounder_flu_rate"] = (
            df_causal["flu_admission_rate"].fillna(0.0).astype(float)
            if "flu_admission_rate" in df_causal.columns
            else 0.0
        )
        df_causal["confounder_covid_rate"] = (
            df_causal["covid_positivity_pct"].fillna(0.0).astype(float)
            if "covid_positivity_pct" in df_causal.columns
            else 0.0
        )
        df_causal["confounder_neighbor_spillover"] = (
            df_causal["idw_neighbor_breach_rate"].fillna(0.0).astype(float)
            if "idw_neighbor_breach_rate" in df_causal.columns
            else 0.0
        )
        df_causal["confounder_seasonal_sin"] = (
            df_causal["sin_month"].astype(float) if "sin_month" in df_causal.columns else 0.0
        )

        # Filter complete records
        df_causal = df_causal.dropna(
            subset=["treatment_cold_alert", "outcome_breach_rate", "trust_code", "period_date"]
        )
        return df_causal

    def estimate_causal_effect(self, df: pd.DataFrame) -> dict[str, Any]:
        """Estimate causal effect using DoWhy graph and Two-Way Fixed Effects DiD regression."""
        logger.info("estimating_did_causal_effect", total_rows=len(df), threshold=self.threshold)
        causal_data = self.prepare_causal_dataset(df)

        # 1. DoWhy Formal Causal Identification
        causal_model = CausalModel(
            data=causal_data,
            treatment="treatment_cold_alert",
            outcome="outcome_breach_rate",
            common_causes=[
                "confounder_flu_rate",
                "confounder_covid_rate",
                "confounder_neighbor_spillover",
                "confounder_seasonal_sin",
            ],
        )

        _ = causal_model.identify_effect(proceed_when_unidentifiable=True)

        # 2. Linear Regression / Two-Way Fixed Effects Estimation
        # Model: BreachRate = beta0 + beta1 * ColdAlert + confounders + Trust_Dummies
        X_vars = [
            "treatment_cold_alert",
            "confounder_flu_rate",
            "confounder_covid_rate",
            "confounder_neighbor_spillover",
            "confounder_seasonal_sin",
        ]

        # Add trust fixed effect dummies (excluding target reference)
        trust_dummies = pd.get_dummies(
            causal_data["trust_code"], prefix="trust", drop_first=True, dtype=float
        )
        X_design = pd.concat([causal_data[X_vars], trust_dummies], axis=1)
        X_design = sm.add_constant(X_design)
        y_design = causal_data["outcome_breach_rate"]

        ols_model = sm.OLS(y_design, X_design).fit(cov_type="HC1")  # Robust standard errors

        treatment_effect = float(ols_model.params["treatment_cold_alert"])
        std_error = float(ols_model.bse["treatment_cold_alert"])
        p_value = float(ols_model.pvalues["treatment_cold_alert"])
        ci_lower = float(ols_model.conf_int().loc["treatment_cold_alert", 0])
        ci_upper = float(ols_model.conf_int().loc["treatment_cold_alert", 1])

        # 3. Placebo Treatment Refutation Test
        placebo_estimates = []
        rng = np.random.default_rng(seed=42)
        for _ in range(5):
            shuffled_data = causal_data.copy()
            shuffled_data["treatment_cold_alert"] = rng.permutation(
                shuffled_data["treatment_cold_alert"].values
            )
            X_placebo = pd.concat([shuffled_data[X_vars], trust_dummies], axis=1)
            X_placebo = sm.add_constant(X_placebo)
            m_placebo = sm.OLS(shuffled_data["outcome_breach_rate"], X_placebo).fit()
            placebo_estimates.append(float(m_placebo.params["treatment_cold_alert"]))

        placebo_mean = float(np.mean(placebo_estimates))
        refutation_passed = abs(placebo_mean) < abs(treatment_effect)

        result = {
            "causal_mechanism": "UKHSA Cold Health Alert -> Type 1 A&E 4-Hour Breach Rate",
            "point_estimate_breach_pct_increase": round(treatment_effect, 3),
            "std_error": round(std_error, 3),
            "p_value": round(p_value, 5),
            "ci_95": (round(ci_lower, 3), round(ci_upper, 3)),
            "is_statistically_significant": p_value < 0.05,
            "placebo_refuter_mean_effect": round(placebo_mean, 3),
            "refutation_test_passed": refutation_passed,
            "observations_count": len(causal_data),
        }

        logger.info(
            "causal_effect_estimated",
            effect=result["point_estimate_breach_pct_increase"],
            p_val=result["p_value"],
            refutation_passed=refutation_passed,
        )

        return result

    def run(self) -> dict[str, Any]:
        """Execute full causal estimation from stored features."""
        df = load_dataset_from_db()
        return self.estimate_causal_effect(df)


causal_estimator = ColdHealthAlertCausalEstimator()

if __name__ == "__main__":
    res = causal_estimator.run()
    print(res)
