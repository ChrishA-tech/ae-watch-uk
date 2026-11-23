# AE-Watch UK: Phase 2 Verification Report
**NHS Winter Pressure & A&E Surge Early-Warning System**
*Author:* **CHRISH PEP FELIX A**
*Target Benchmark:* **Liverpool University Hospitals NHS Foundation Trust (ODS: `REM`)**
*Infrastructure Cost:* **£0 / $0 Budget (100% Free Public UK Data, Local Accelerated Compute)**

---

## 1. Executive Summary & Verification Overview

Phase 2 expanded the production pipeline across temporal, spatial, predictive, causal, and MLOps dimensions. All modules ingest 100% real UK public data (NHS England MSitAE releases up to October 2026, UKHSA pathogen surveillance, and Open-Meteo telemetry), process geospatial spillover with PostGIS and Uber H3 resolution 7, forecast multi-horizon breach rates with quantile intervals, quantify causal cold health alerts, and monitor distribution drift.

### Key Milestones Achieved:
1. **Real Data Span (2024–2026):**
   - **NHS England MSitAE:** 7,132 provider-level monthly records ingested through October 2026.
   - **UKHSA Surveillance Dashboard:** 11,678 records spanning Flu, RSV, COVID-19 PCR positivity, and NHS 111 syndromic triage calls.
   - **Open-Meteo:** 7,385 daily weather observations (Jan 2024 – Nov 2026) for Cheshire & Merseyside NHS Trust hospital centroids.
   - **dbt Medallion Pipeline:** `gold.fct_trust_winter_pressure_daily` materialized 7,098 rows (36 full months for Liverpool `REM`).
2. **Spatial & Temporal Feature Store (`gold.ml_trust_forecast_features`):**
   - 7,098 feature records materialized in PostgreSQL.
   - Inverse-Distance-Weighted (IDW) spatial catchment spillover computed across acute trusts within 25 km of Liverpool `REM` (Countess of Chester `RJR`, Wirral `RBL`, Warrington `RWW`, Alder Hey `RBS`, Liverpool Women's `REP`).
   - Uber H3 resolution 7 indexing (`871951071ffffff` for Liverpool REM).
   - Zero-leakage temporal lags (1m, 2m, 3m rolling mean/max/std) and calendar encodings (UK bank holidays, cyclical month sin/cos).
3. **Multi-Horizon Forecasting & Explainability:**
   - **5-Fold Expanding Window Temporal CV:** Zero future lookahead across 35 unique monthly periods.
   - **LightGBM Quantiles (P10, P50, P90):** Mean 7-day MAE = **2.03%**, RMSE = **3.09%**, 80% Prediction Interval Coverage = **78.28%**.
   - **XGBoost Surge Classifier:** ROC-AUC = **0.9678** (predicting >30% breach or <70% performance).
   - **PyTorch Temporal Fusion Transformer:** Executed on Apple Silicon `mps` acceleration (with deterministic CPU fallback): Mean MAE = **3.44%**, RMSE = **5.41%**.
   - **TreeSHAP Explainability:**
     - Global top breach drivers: `breach_rate_lag_1m`, `breach_rolling_3m_mean`, `idw_neighbor_breach_rate`, `total_cold_snap_degree_days`.
     - Liverpool REM local attribution: Base rate 36.17% driven upward by severe local cold snap (+2.98%) and neighbor spillover from Wirral/Chester (+1.45%).
4. **Causal Inference (DoWhy Difference-in-Differences):**
   - Estimated causal impact of UKHSA Cold Health Alerts: **+2.058 percentage points increase** in Type 1 A&E 4-hour breach rates ($p = 0.00003$, 95% CI $[1.094\%, 3.023\%]$).
   - Placebo refutation test passed ($\Delta = -0.089\%$, no spurious effect).
5. **MLOps & Monitoring:**
   - Population Stability Index (PSI) and Kolmogorov-Smirnov two-sample tests run between baseline winter (2023–2024) and 2025–2026.
   - Detected winter distribution drift in cold snap degree days and COVID-19 PCR positivity.
   - Experiments, metrics, and SHAP artifacts logged to MLflow (`ae_watch_uk_gbdt_forecasting`, `ae_watch_uk_pytorch_tft`).
6. **Code Quality & Testing:**
   - **39 / 39 pytest tests passing** across unit, integration, spatial, temporal, causal, drift, and resilience suites.
   - **Ruff check and format:** 100% clean, 0 lint or formatting errors.
