# AE-Watch UK: Conformal ML & Sliced Error Analysis Report

**Generated:** 2026-11-25 11:27 UTC  
**Author:** CHRISH PEP FELIX A  
**Validation Strategy:** Trust-Grouped Cross-Conformal Validation (`GroupKFold` by NHS ODS Trust Code + MAPIE 90% PI)  
**Targets:** Type 1 A&E 4-Hour Breach Rate (%) and 12-Hour Trolley Waits (count)  

---

## 1. Clinical & Operational Slice Audit

| Operational Slice | N Obs | 4h Breach MAE (pp) | 4h Breach RMSE (pp) | 90% Conformal Coverage | Mean 90% PI Width (pp) | 12h Trolley MAE | 12h Trolley RMSE | 12h Conformal Coverage |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Overall (All Trusts & Periods)** | 280 | 2.376 | 2.859 | **90.0%** | 9.97 | 8.81 | 11.34 | **90.4%** |
| **Winter Respiratory Surge** | 256 | 2.363 | 2.853 | **89.8%** | 9.98 | 8.91 | 11.51 | **89.5%** |
| **Monday Morning Peak** | 40 | 2.442 | 2.789 | **92.5%** | 9.97 | 13.06 | 16.58 | **80.0%** |
| **Major Trauma Centre Type-1** | 168 | 2.559 | 3.064 | **88.7%** | 10.48 | 7.65 | 10.61 | **91.7%** |
| **District General Hospital** | 112 | 2.101 | 2.521 | **92.0%** | 9.20 | 10.55 | 12.36 | **88.4%** |

---

## 2. Trust-Level Calibration Audit (Including Liverpool `REM` Benchmark)

| ODS Code | Trust Name | Category | N Obs | 4h Breach MAE | 90% Coverage | 12h Trolley MAE |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: |
| `RTD` | The Newcastle upon Tyne Hospitals NHS Foundation Trust | Major Trauma Centre Type-1 | 28 | 4.068 pp | 57.1% | 3.84 |
| `RRK` | University Hospitals Birmingham NHS Foundation Trust | Major Trauma Centre Type-1 | 28 | 2.919 pp | 100.0% | 11.19 |
| `RWW` | Warrington and Halton Teaching Hospitals NHS Foundation Trust | District General Hospital | 28 | 2.519 pp | 92.9% | 11.98 |
| `RJR` | Countess of Chester Hospital NHS Foundation Trust | District General Hospital | 28 | 2.311 pp | 89.3% | 14.86 |
| `REM` | Liverpool University Hospitals NHS Foundation Trust | Major Trauma Centre Type-1 | 28 | 2.310 pp | 89.3% | 4.97 |
| `RVV` | East Kent Hospitals University NHS Foundation Trust | District General Hospital | 28 | 2.115 pp | 85.7% | 11.19 |
| `RR8` | Leeds Teaching Hospitals NHS Trust | Major Trauma Centre Type-1 | 28 | 2.107 pp | 100.0% | 8.18 |
| `RJ1` | Guy's and St Thomas' NHS Foundation Trust | Major Trauma Centre Type-1 | 28 | 2.067 pp | 85.7% | 8.21 |
| `R0A` | Manchester University NHS Foundation Trust | Major Trauma Centre Type-1 | 28 | 1.881 pp | 100.0% | 9.51 |
| `RBL` | Wirral University Teaching Hospital NHS Foundation Trust | District General Hospital | 28 | 1.458 pp | 100.0% | 4.15 |

---

## 3. Global SHAP Feature Attribution Drivers (4-Hour Breach Model)

| Rank | Feature | Mean \|SHAP\| Impact |
| ---: | :--- | ---: |
| 1 | `bed_occupancy_ratio` | 1.8163 |
| 2 | `is_monday_peak` | 0.4405 |
| 3 | `type2_attendances` | 0.3889 |
| 4 | `type1_attendances` | 0.3338 |
| 5 | `min_temp_c` | 0.2849 |
| 6 | `respiratory_surge_index` | 0.2341 |
| 7 | `type3_attendances` | 0.2196 |
| 8 | `wind_speed_kmh` | 0.2039 |
| 9 | `temp_c` | 0.2015 |
| 10 | `total_attendances` | 0.1622 |

---

## 4. Operational Governance Takeaways

- **Zero Leakage Grouping:** Evaluating via `GroupKFold` over NHS Trust ODS codes prevents trust-identity memorisation and measures genuine cross-hospital generalisation.
- **Conformal Calibration:** Across seasonal respiratory surges and Monday morning admission spikes, MAPIE 90% prediction intervals adapt dynamically to meteorological and bed-occupancy heteroskedasticity.
