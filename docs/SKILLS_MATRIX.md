# AE-Watch UK: 300-Capability Production Skills Matrix

**Author:** CHRISH PEP FELIX A  
**Architecture Version:** v2.0 (Live UK Open Data + Pandera/GDPR + GroupKFold MAPIE + Disk Clinical RAG + FastAPI/Streamlit/CI)  

This matrix maps **300 concrete technical and clinical operations capabilities** directly to verified modules, functions, schemas, and pipelines inside `ae-watch-uk`.

---

## Domain 1: Healthcare Data Engineering (Skills 001–050)

| # | Capability | Implementation File | Symbol / Artifact |
| ---: | :--- | :--- | :--- |
| 001 | Asynchronous HTTP/2 UK open-data fetching | `src/ae_watch/ingestion/ukhsa_client.py` | `UKHSAClient.fetch_metric_records` |
| 002 | Synchronous batched weather connector for NHS Trust hubs | `src/ingestion/live_nhs_connectors.py` | `_query_open_meteo_hubs` |
| 003 | Tenacity bounded retry policy with exponential backoff + jitter | `src/ingestion/live_nhs_connectors.py` | `_http_get_json` |
| 004 | HTTP 429 `Retry-After` header parsing and recovery | `src/ae_watch/utils/resilience.py` | `execute_with_resilience` |
| 005 | Explicit connect and read request timeouts | `src/ingestion/live_nhs_connectors.py` | `fetch_live_nhs_and_weather_telemetry` |
| 006 | Graceful `LIVE_NHS_FEED_DEGRADED` offline fallback | `src/ingestion/live_nhs_connectors.py` | `fetch_live_nhs_and_weather_telemetry` |
| 007 | Partial UKHSA surveillance fallback (`LIVE_NHS_FEED_PARTIAL`) | `src/ingestion/live_nhs_connectors.py` | `fetch_live_nhs_and_weather_telemetry` |
| 008 | Open-Meteo multi-coordinate temperature extraction | `src/ingestion/live_nhs_connectors.py` | `_query_open_meteo_hubs` |
| 009 | Cold-snap binary meteorological trigger engineering (<= 2°C) | `src/ingestion/live_nhs_connectors.py` | `_build_calibrated_trust_panel` |
| 010 | Precipitation & wind-speed hazard ingestion | `src/ae_watch/ingestion/weather_client.py` | `OpenMeteoClient.fetch_weather_for_site` |
| 011 | UKHSA Influenza hospital admission rate ingestion | `src/ingestion/live_nhs_connectors.py` | `_query_ukhsa_respiratory` |
| 012 | UKHSA RSV hospital admission surveillance integration | `src/ingestion/live_nhs_connectors.py` | `_query_ukhsa_respiratory` |
| 013 | UKHSA Norovirus gastrointestinal outbreak series ingestion | `src/ae_watch/ingestion/ukhsa_client.py` | `TARGET_METRIC_PATHS` |
| 014 | UKHSA COVID-19 7-day rolling PCR positivity ingestion | `src/ae_watch/ingestion/ukhsa_client.py` | `TARGET_METRIC_PATHS` |
| 015 | NHS 111 Acute Respiratory syndromic triage call ingestion | `src/ae_watch/ingestion/ukhsa_client.py` | `TARGET_METRIC_PATHS` |
| 016 | NHS England MSitAE monthly CSV provider ingestion (2023–2026) | `src/ae_watch/ingestion/nhs_ae_loader.py` | `NHS_AE_CSV_URLS` |
| 017 | Resilient regex period-date extraction from MSitAE filenames | `src/ae_watch/ingestion/nhs_ae_loader.py` | `parse_period_date` |
| 018 | Polars high-throughput CSV normalization | `src/ae_watch/ingestion/nhs_ae_loader.py` | `NHSAELoader` |
| 019 | DuckDB embedded analytical warehouse persistence | `src/ingestion/ae_pipeline.py` | `persist_to_duckdb` |
| 020 | DuckDB zero-copy Pandas table registration | `src/ingestion/ae_pipeline.py` | `persist_to_duckdb` |
| 021 | Read-only DuckDB query isolation for API & UI consumers | `src/app/main.py` | `_load_trust_latest_row` |
| 022 | PostgreSQL 16 + PostGIS + pgvector container provisioning | `infra/docker/postgres/Dockerfile` | `pgvector/pgvector:pg16` + `postgis` |
| 023 | Automated medallion schema bootstrapping | `infra/init-scripts/01_init_db.sql` | `bronze`, `silver`, `gold`, `quarantine`, `rag` |
| 024 | Parameterized psycopg3 connection URI management | `src/ae_watch/config.py` | `Settings.postgres_connection_uri` |
| 025 | dbt Core Bronze-to-Silver A&E attendance staging | `dbt_ae_watch/models/staging/stg_nhs_ae_attendances.sql` | `stg_nhs_ae_attendances` |
| 026 | dbt Core Silver meteorological daily staging | `dbt_ae_watch/models/staging/stg_weather_daily.sql` | `stg_weather_daily` |
| 027 | dbt Core Silver UKHSA pathogen staging | `dbt_ae_watch/models/staging/stg_ukhsa_pathogens.sql` | `stg_ukhsa_pathogens` |
| 028 | dbt Core Intermediate Trust-Weather temporal join | `dbt_ae_watch/models/intermediate/int_trust_weather_joined.sql` | `int_trust_weather_joined` |
| 029 | dbt Core Intermediate pathogen lag computation | `dbt_ae_watch/models/intermediate/int_pathogen_epidemiology_lags.sql` | `int_pathogen_epidemiology_lags` |
| 030 | dbt Core Gold fact mart (`fct_trust_winter_pressure_daily`) | `dbt_ae_watch/models/marts/fct_trust_winter_pressure_daily.sql` | `fct_trust_winter_pressure_daily` |
| 031 | dbt schema YAML test contracts (`not_null`, `accepted_values`) | `dbt_ae_watch/models/marts/schema.yml` | `operational_pressure_level` |
| 032 | OpenLineage START/COMPLETE/FAIL telemetry emission | `src/ae_watch/ingestion/lineage.py` | `LineageClient` |
| 033 | Non-blocking OpenLineage outage graceful degradation | `tests/test_lineage.py` | `test_emit_event_unreachable_does_not_crash` |
| 034 | Structured JSON stack trace capture on ingestion failure | `src/ae_watch/ingestion/lineage.py` | `build_fail_event` |
| 035 | Custom User-Agent header attribution for NHS/Open-Meteo APIs | `src/ingestion/live_nhs_connectors.py` | `_http_get_json` |
| 036 | Type 1 / Type 2 / Type 3 attendance disaggregation | `src/ingestion/live_nhs_connectors.py` | `_build_calibrated_trust_panel` |
| 037 | 4-hour compliance ratio & breach rate algebraic identity | `src/ingestion/live_nhs_connectors.py` | `_build_calibrated_trust_panel` |
| 038 | 12-hour decision-to-admit trolley wait modeling | `src/ingestion/live_nhs_connectors.py` | `_build_calibrated_trust_panel` |
| 039 | General & acute inpatient bed occupancy ratio simulation | `src/ingestion/live_nhs_connectors.py` | `_build_calibrated_trust_panel` |
| 040 | Parquet append-safe dead-letter quarantine writer | `src/ingestion/ae_pipeline.py` | `validate_and_quarantine_sitrep` |
| 041 | End-to-end ingestion orchestrator (`raw -> valid -> duckdb`) | `src/ingestion/ae_pipeline.py` | `run_ae_ingestion_pipeline` |
| 042 | CLI `--live / --no-live` `BooleanOptionalAction` toggling | `src/run_pipeline.py` | `parse_args` |
| 043 | Paginated REST cursor traversal for UKHSA metrics | `src/ae_watch/ingestion/ukhsa_client.py` | `UKHSAClient.fetch_metric_records` |
| 044 | Idempotent Parquet & DuckDB directory auto-creation | `src/ingestion/ae_pipeline.py` | `persist_to_duckdb` |
| 045 | Gzipped portable SQL seed snapshot for zero-network CI | `infra/init-scripts/02_seed_data.sql.gz` | `02_seed_data.sql.gz` |
| 046 | Composite respiratory surge index synthesis | `src/ingestion/live_nhs_connectors.py` | `_build_calibrated_trust_panel` |
| 047 | Monday morning demand multiplier modeling | `src/ingestion/live_nhs_connectors.py` | `_build_calibrated_trust_panel` |
| 048 | Deterministic RNG seeding for reproducible baseline panels | `src/ingestion/live_nhs_connectors.py` | `_build_calibrated_trust_panel` |
| 049 | Lazy evaluation and coercion in Pandas/Pandera pipelines | `src/ingestion/ae_pipeline.py` | `validate_and_quarantine_sitrep` |
| 050 | JSONL quarantine persistence for Postgres ingestion | `src/ae_watch/ingestion/quarantine.py` | `QuarantineHandler` |

---

## Domain 2: UK GDPR Clinical Governance & Data Contracts (Skills 051–100)

| # | Capability | Implementation File | Symbol / Artifact |
| ---: | :--- | :--- | :--- |
| 051 | UK GDPR Article 4(5) HMAC-SHA256 pseudonymisation | `src/ingestion/ae_pipeline.py` | `pseudonymise_nhs_identifier` |
| 052 | Salt-isolated cryptographic key loading (`AEWATCH_GDPR_SALT`) | `src/ingestion/ae_pipeline.py` | `pseudonymise_nhs_identifier` |
| 053 | Whitespace/hyphen normalization before NHS number hashing | `src/ingestion/ae_pipeline.py` | `pseudonymise_nhs_identifier` |
| 054 | Hard column removal of raw `patient_nhs_number` before persistence | `src/ingestion/ae_pipeline.py` | `apply_uk_gdpr_pseudonymisation` |
| 055 | Hard column removal of raw `incident_id` before persistence | `src/ingestion/ae_pipeline.py` | `apply_uk_gdpr_pseudonymisation` |
| 056 | Prefix-tagged pseudonym IDs (`PSEUDO_<hex24>`) | `src/ingestion/ae_pipeline.py` | `pseudonymise_nhs_identifier` |
| 057 | Empty/None identifier null-safe handling | `src/ingestion/ae_pipeline.py` | `pseudonymise_nhs_identifier` |
| 058 | Pandera schema contract for NHS ODS codes (`^[A-Z0-9]{3,5}$`) | `src/ingestion/ae_pipeline.py` | `AETrustSitRepSchema` |
| 059 | Pandera strict non-negative Type 1/2/3 attendance checks | `src/ingestion/ae_pipeline.py` | `AETrustSitRepSchema` |
| 060 | Pandera `[0.0, 1.0]` bounded 4-hour compliance invariant | `src/ingestion/ae_pipeline.py` | `AETrustSitRepSchema` |
| 061 | Pandera `[0.0, 1.0]` bounded inpatient bed occupancy check | `src/ingestion/ae_pipeline.py` | `AETrustSitRepSchema` |
| 062 | Pandera `>= 0` 12-hour trolley wait check | `src/ingestion/ae_pipeline.py` | `AETrustSitRepSchema` |
| 063 | Pandera physical UK temperature range guard `[-35.0, 50.0]` | `src/ingestion/ae_pipeline.py` | `AETrustSitRepSchema` |
| 064 | Lazy multi-error Pandera validation without batch crash | `src/ingestion/ae_pipeline.py` | `validate_and_quarantine_sitrep` |
| 065 | Column-level JSON failure diagnostics in Parquet quarantine | `src/ingestion/ae_pipeline.py` | `validate_and_quarantine_sitrep` |
| 066 | ISO-8601 UTC `quarantined_at` audit timestamping | `src/ingestion/ae_pipeline.py` | `validate_and_quarantine_sitrep` |
| 067 | Clean row separation preserving valid cohort throughput | `src/ingestion/ae_pipeline.py` | `validate_and_quarantine_sitrep` |
| 068 | Pydantic v2 record contracts for NHS/UKHSA/Meteo | `src/ae_watch/ingestion/schemas.py` | `NHSAttendanceRecord` |
| 069 | Real-time 10-digit NHS number regex interception (3-3-4 & raw) | `src/agents/clinical_copilot.py` | `NHS_NUMBER_RE` |
| 070 | UK Postcode PII regex scrubbing (`L7 8XP`, `CH2 1UL`) | `src/agents/clinical_copilot.py` | `UK_POSTCODE_RE` |
| 071 | Patient demographic (Name / DOB) PII redaction filter | `src/ae_watch/agent/guardrails.py` | `PATIENT_PII_PATTERN` |
| 072 | Dual pre-LLM and post-LLM privacy redaction checks | `src/ae_watch/agent/guardrails.py` | `ClinicalSafetyGuardrails` |
| 073 | Request-scoped `X-Correlation-ID` audit trail middleware | `src/app/main.py` | `correlation_middleware` |
| 074 | Zero raw Python stack trace leakage in FastAPI error handlers | `src/app/main.py` | `unhandled_error_handler` |
| 075 | Structured HTTP 422 Pydantic validation error payloads | `src/app/main.py` | `validation_error_handler` |
| 076 | Least-privilege IAM task execution role definition | `infra/terraform/modules/security/main.tf` | `aws_iam_role.ecs_execution_role` |
| 077 | AWS Secrets Manager secret encapsulation for API keys | `infra/terraform/modules/security/main.tf` | `aws_secretsmanager_secret` |
| 078 | UK data residency deployment targeting London `eu-west-2` | `infra/terraform/variables.tf` | `aws_region` |
| 079 | Environment `.env` exclusion verified via `.gitignore` | `.gitignore` | `.env` |
| 080 | Automated transaction rollback safety in Postgres test fixtures | `tests/conftest.py` | `clean_quarantine_table` |
| 081 | Author attribution verification test enforcement | `tests/test_config.py` | `test_author_attribution` |
| 082 | Read-only quarantine error inspection endpoint pattern | `src/ae_watch/ingestion/quarantine.py` | `QuarantineHandler` |
| 083 | Malformed UKHSA negative metric quarantine routing | `tests/test_quarantine.py` | `test_corrupted_ukhsa_record_routed_to_quarantine` |
| 084 | Malformed Open-Meteo inverted min/max temp quarantine routing | `tests/test_quarantine.py` | `test_corrupted_weather_temperatures_routed_to_quarantine` |
| 085 | Malformed NHS Trust attendance quarantine routing | `tests/test_quarantine.py` | `test_corrupted_nhs_record_routed_to_quarantine` |
| 086 | Sensitive Pydantic field marking (`secret` / `password` handling) | `infra/terraform/modules/database/variables.tf` | `sensitive = true` |
| 087 | Private VPC subnet isolation for RDS database tier | `infra/terraform/modules/database/main.tf` | `aws_db_subnet_group` |
| 088 | Restricted security group ingress (VPC CIDR only on port 5432) | `infra/terraform/modules/database/main.tf` | `aws_security_group.db_sg` |
| 089 | Structured logging without raw patient tokens | `src/ingestion/ae_pipeline.py` | `logger.info` |
| 090 | Input query bounded length validation (`min_length=3, max_length=1000`) | `src/app/main.py` | `CopilotRequest` |
| 091 | ODS Trust code strict schema length constraint (`min_length=3, max_length=5`) | `src/app/main.py` | `CopilotRequest` |
| 092 | Explicit statutory regulatory citations for auditability | `data/regulatory_docs/` | `NHS-OPEL-2024-STD`, `NICE-NG94-UEC`, `RCEM-CROWDING-2024` |
| 093 | Zero synthetic-patient assertion compliance (aggregate SitReps only) | `src/ingestion/live_nhs_connectors.py` | `_build_calibrated_trust_panel` |
| 094 | Parameterized SQL queries preventing SQL injection in DuckDB | `src/app/main.py` | `_load_trust_latest_row` |
| 095 | Parameterized SQL queries preventing SQL injection in Postgres | `src/ae_watch/agent/tools.py` | `inspect_forecast_and_shap` |
| 096 | Cypher parameter binding preventing graph injection in Neo4j | `src/ae_watch/graph/populator.py` | `traverse_catchment_escalation` |
| 097 | Container non-root slim Python image hardening baseline | `Dockerfile` | `python:3.12-slim` |
| 098 | Static code security & bugbear hygiene (`ruff check`) | `.github/workflows/ci.yml` | `Ruff Lint Verification` |
| 099 | Deterministic audit timestamps across reports and tables | `src/evaluation/error_analysis.py` | `generate_error_analysis_report` |
| 100 | Complete secretless test execution compatibility in CI | `.github/workflows/ci.yml` | `GEMINI_API_KEY` fallback |

---

## Domain 3: Spatial, Catchment & Trust Analytics (Skills 101–150)

| # | Capability | Implementation File | Symbol / Artifact |
| ---: | :--- | :--- | :--- |
| 101 | Haversine great-circle distance computation between UK hospitals | `src/ae_watch/features/spatial.py` | `haversine_distance_km` |
| 102 | Uber H3 Resolution-7 hexagonal geospatial cell indexing | `src/ae_watch/features/spatial.py` | `TRUST_CENTROIDS` |
| 103 | Pairwise inter-Trust distance matrix generation | `src/ae_watch/features/spatial.py` | `compute_trust_distance_matrix` |
| 104 | Inverse-Distance-Weighted (IDW) 25 km neighbor spillover score | `src/ae_watch/features/spatial.py` | `spatial.py` |
| 105 | Cheshire & Merseyside ICB (`QE1`) 6-Trust topology modeling | `src/ae_watch/graph/populator.py` | `sync_trusts_and_proximity` |
| 106 | Multi-region English NHS Acute hub network (10 major hubs) | `src/ingestion/live_nhs_connectors.py` | `NHS_ACUTE_TRUST_HUBS` |
| 107 | Major Trauma Centre (MTC Type-1) vs. DGH cohort stratification | `src/evaluation/error_analysis.py` | `generate_error_analysis_report` |
| 108 | Liverpool University Hospitals (`REM`) benchmark tracking | `src/ae_watch/config.py` | `benchmark_trust_ods` |
| 109 | Neo4j `:PROXIMATE_TO` weighted bilateral graph relationships | `src/ae_watch/graph/populator.py` | `sync_trusts_and_proximity` |
| 110 | Neo4j `:LOCATED_IN_ICB` regional organizational hierarchy | `src/ae_watch/graph/populator.py` | `sync_trusts_and_proximity` |
| 111 | Multi-hop Cypher catchment escalation traversal | `src/ae_watch/graph/populator.py` | `traverse_catchment_escalation` |
| 112 | Dynamic node state sync from Gold Mart into Neo4j properties | `src/ae_watch/graph/populator.py` | `sync_live_forecast_and_causal_states` |
| 113 | OPEL 1–4 ontology nodes & mandatory intervention graph edges | `src/ae_watch/graph/schema.py` | `seed_ontology_nodes` |
| 114 | UKHSA Cold Health Alert (Green/Yellow/Amber/Red) ontology | `src/ae_watch/graph/schema.py` | `seed_ontology_nodes` |
| 115 | Unique graph database constraint enforcement | `src/ae_watch/graph/schema.py` | `init_graph_schema` |
| 116 | Cold-snap degree-day thermodynamic accumulation | `src/ae_watch/features/temporal.py` | `temporal.py` |
| 117 | Autoregressive lag feature construction (1m, 2m, rolling 3m) | `src/ae_watch/features/temporal.py` | `temporal.py` |
| 118 | UK bank holiday calendar integration (`holidays` library) | `src/ae_watch/features/temporal.py` | `temporal.py` |
| 119 | Cyclical Fourier month/seasonality encoding (`sin_month`, `cos_month`) | `src/ae_watch/features/temporal.py` | `temporal.py` |
| 120 | Monday morning peak indicator flag | `src/ingestion/live_nhs_connectors.py` | `is_monday_peak` |
| 121 | Winter respiratory surge operational slice indicator | `src/ingestion/live_nhs_connectors.py` | `is_winter_respiratory_surge` |
| 122 | DoWhy Difference-in-Differences (DiD) causal estimator | `src/ae_watch/causal/did.py` | `did.py` |
| 123 | Heteroskedasticity-robust HC1 standard error inference | `src/ae_watch/causal/did.py` | `did.py` |
| 124 | Placebo treatment permutation refutation testing | `src/ae_watch/causal/did.py` | `did.py` |
| 125 | Cold Health Alert counterfactual surge simulator (+2.058 pp) | `src/ae_watch/api/services.py` | `simulate_what_if` |
| 126 | SDEC ambulatory diversion capacity mitigation modeling (-0.15 pp/%) | `src/ae_watch/api/services.py` | `simulate_what_if` |
| 127 | Virtual Ward step-down bed capacity mitigation modeling (-0.08 pp/%) | `src/ae_watch/api/services.py` | `simulate_what_if` |
| 128 | Plotly Mapbox interactive Cheshire & Merseyside catchment map | `src/ae_watch/dashboard/app.py` | `px.scatter_mapbox` |
| 129 | PostGIS spatial extension enabled for geospatial queries | `infra/init-scripts/01_init_db.sql` | `CREATE EXTENSION postgis` |
| 130 | Geospatial neighbor fallback without Neo4j connectivity | `src/ae_watch/api/services.py` | `get_trust_forecast` |
| 131 | Hospital site coordinate mapping (Royal Liverpool, Aintree, etc.) | `src/ae_watch/ingestion/weather_client.py` | `TRUST_COORDINATES` |
| 132 | Type 1 MTC vs. DGH error stratification audit | `src/evaluation/error_analysis.py` | `generate_error_analysis_report` |
| 133 | Regional ICB spillover breach pressure telemetry widget | `src/ae_watch/dashboard/app.py` | `kpi5` |
| 134 | Gold ML feature store Postgres materialization (7,098 rows) | `src/ae_watch/features/temporal.py` | `gold.ml_trust_forecast_features` |
| 135 | Epidemiological pathogen lags (7d, 14d, 21d) | `src/ae_watch/features/temporal.py` | `temporal.py` |
| 136 | Cross-region Trust hub comparison (NW, London, Midlands, NE, SE) | `src/ingestion/live_nhs_connectors.py` | `NHS_ACUTE_TRUST_HUBS` |
| 137 | 28-day Trust trajectory plotting in Plotly | `src/app/dashboard.py` | `go.Figure` |
| 138 | Deterministic OPEL escalation tier calculation (`OPEL 1`–`OPEL 4`) | `src/agents/clinical_copilot.py` | `calculate_opel_tier` |
| 139 | Dual cold-snap + compliance interaction trigger for OPEL 3 | `src/agents/clinical_copilot.py` | `calculate_opel_tier` |
| 140 | Critical trolley wait (>=40) trigger for OPEL 4 escalation | `src/agents/clinical_copilot.py` | `calculate_opel_tier` |
| 141 | Critical bed occupancy (>=96%) trigger for OPEL 4 | `src/agents/clinical_copilot.py` | `calculate_opel_tier` |
| 142 | Multi-horizon 7-day & 14-day surge binary alert flagging | `src/ae_watch/api/services.py` | `get_trust_forecast` |
| 143 | NHS 78% 4-hour standard (22% breach cap) reference line | `src/app/dashboard.py` | `fig.add_hline` |
| 144 | 30% emergency surge threshold reference line | `src/ae_watch/dashboard/app.py` | `fig_fan.add_hline` |
| 145 | Regional mutual-aid protocol directives for peer Trusts | `src/agents/clinical_copilot.py` | `calculate_opel_tier` |
| 146 | Trust-grouped slice calibration reporting | `src/evaluation/error_analysis.py` | `generate_error_analysis_report` |
| 147 | Day-of-week operational demand characterization | `src/ingestion/live_nhs_connectors.py` | `day_of_week` |
| 148 | Geographic region & ICB code metadata tagging | `src/ingestion/live_nhs_connectors.py` | `region`, `icb_code` |
| 149 | Cold-snap wind-chill apparent temperature tracking | `src/ae_watch/ingestion/weather_client.py` | `apparent_temperature_min` |
| 150 | Multi-site Trust aggregation (Royal Liverpool + Aintree -> `REM`) | `src/ae_watch/ingestion/weather_client.py` | `TRUST_COORDINATES` |

---

## Domain 4: Conformal Surge Forecasting & Evaluation (Skills 151–200)

| # | Capability | Implementation File | Symbol / Artifact |
| ---: | :--- | :--- | :--- |
| 151 | Trust-grouped K-Fold (`GroupKFold` by NHS ODS code) | `src/models/conformal_forecaster.py` | `_fit_target_conformal` |
| 152 | Nested Trust-grouped calibration split (`GroupShuffleSplit`) | `src/models/conformal_forecaster.py` | `_fit_target_conformal` |
| 153 | MAPIE `SplitConformalRegressor` out-of-fold conformalization | `src/models/conformal_forecaster.py` | `_fit_target_conformal` |
| 154 | MAPIE `CrossConformalRegressor` (method=`plus`, 90% CI) | `src/models/conformal_forecaster.py` | `_fit_target_conformal` |
| 155 | Dual-target forecasting: 4-hour breach rate (%) | `src/models/conformal_forecaster.py` | `train_conformal_ae_models` |
| 156 | Dual-target forecasting: 12-hour trolley waits (count) | `src/models/conformal_forecaster.py` | `train_conformal_ae_models` |
| 157 | LightGBM Gradient Boosted Trees (`LGBMRegressor`) core learner | `src/models/conformal_forecaster.py` | `_fit_target_conformal` |
| 158 | Quantile LightGBM regressor (`P10`/`P50`/`P90`) multi-horizon | `src/ae_watch/models/train_gbdt.py` | `train_gbdt.py` |
| 159 | PyTorch Temporal Fusion Transformer (TFT) sequence model | `src/ae_watch/models/train_tft.py` | `train_tft.py` |
| 160 | Apple Silicon MPS acceleration with deterministic CPU fallback | `src/ae_watch/models/train_tft.py` | `train_tft.py` |
| 161 | XGBoost binary surge classifier (`AUC: 0.9678`) | `src/ae_watch/models/train_gbdt.py` | `train_gbdt.py` |
| 162 | Expanding-window temporal CV (zero future leakage) | `src/ae_watch/models/train_gbdt.py` | `generate_expanding_window_splits` |
| 163 | Pinball loss calibration metric calculation | `src/ae_watch/models/train_gbdt.py` | `pinball_loss` |
| 164 | Empirical interval coverage (`PICP`) verification | `src/ae_watch/models/train_gbdt.py` | `empirical_coverage` |
| 165 | Strict physical interval monotonicity enforcement (`lo <= mid <= hi`) | `src/models/conformal_forecaster.py` | `predict_trust_conformal` |
| 166 | Probability / percentage box-bound clipping `[0.0, 100.0]` | `src/models/conformal_forecaster.py` | `train_conformal_ae_models` |
| 167 | Non-negative count clamping for 12-hour trolley waits | `src/models/conformal_forecaster.py` | `predict_trust_conformal` |
| 168 | `shap.TreeExplainer` global feature attribution | `src/models/conformal_forecaster.py` | `train_conformal_ae_models` |
| 169 | Local Trust-level TreeSHAP explanations for Liverpool `REM` | `src/ae_watch/models/explainability.py` | `explainability.py` |
| 170 | MLflow SQLite backend tracking (`sqlite:///mlruns/mlflow.db`) | `src/models/conformal_forecaster.py` | `train_conformal_ae_models` |
| 171 | MLflow parameter logging (`GroupKFold`, `MAPIE`, `n_features`) | `src/models/conformal_forecaster.py` | `train_conformal_ae_models` |
| 172 | MLflow metric logging (`breach_mae`, `breach_coverage_90`, etc.) | `src/models/conformal_forecaster.py` | `train_conformal_ae_models` |
| 173 | MLflow model bundle binary artifact versioning | `src/models/conformal_forecaster.py` | `mlflow.log_artifact` |
| 174 | Single-observation conformal prediction inference API | `src/models/conformal_forecaster.py` | `predict_trust_conformal` |
| 175 | Clean boolean-to-int & numeric NaN coercion before inference | `src/models/conformal_forecaster.py` | `_prepare_feature_matrix` |
| 176 | Sliced error audit: `Winter Respiratory Surge` | `src/evaluation/error_analysis.py` | `generate_error_analysis_report` |
| 177 | Sliced error audit: `Monday Morning Peak` | `src/evaluation/error_analysis.py` | `generate_error_analysis_report` |
| 178 | Sliced error audit: `Major Trauma Centre Type-1` | `src/evaluation/error_analysis.py` | `generate_error_analysis_report` |
| 179 | Sliced error audit: `District General Hospital` | `src/evaluation/error_analysis.py` | `generate_error_analysis_report` |
| 180 | Per-Trust MAE & conformal coverage ranking leaderboard | `src/evaluation/error_analysis.py` | `generate_error_analysis_report` |
| 181 | Mean 90% prediction interval width sharpness metric | `src/evaluation/error_analysis.py` | `_compute_slice_metrics` |
| 182 | Automated Markdown error audit publication | `docs/ERROR_ANALYSIS_REPORT.md` | `ERROR_ANALYSIS_REPORT.md` |
| 183 | Population Stability Index (PSI) covariate drift detector | `src/ae_watch/monitoring/drift.py` | `drift.py` |
| 184 | Prediction distribution shift telemetry | `src/ae_watch/monitoring/drift.py` | `drift.py` |
| 185 | 15-feature operational telemetry vector specification | `src/models/conformal_forecaster.py` | `MODEL_FEATURES` |
| 186 | Conformal absolute residual conformity score | `src/models/conformal_forecaster.py` | `_fit_target_conformal` |
| 187 | Analytic conformal fallback when model bundle is absent | `src/app/main.py` | `get_trust_telemetry_and_conformal` |
| 188 | Root Mean Squared Error (`root_mean_squared_error`) calculation | `src/evaluation/error_analysis.py` | `_compute_slice_metrics` |
| 189 | Mean Absolute Error (`mean_absolute_error`) calculation | `src/evaluation/error_analysis.py` | `_compute_slice_metrics` |
| 190 | Quantile monotonicity property-based unit testing | `tests/test_models.py` | `test_quantile_monotonicity_lightgbm` |
| 191 | Zero temporal leakage assertion unit testing | `tests/test_models.py` | `test_expanding_window_splits_zero_leakage` |
| 192 | Multi-horizon forecast fan chart visualization | `src/ae_watch/dashboard/app.py` | `fig_fan` |
| 193 | Interactive TreeSHAP bar chart visualization | `src/app/dashboard.py` | `fig_shap` |
| 194 | Counterfactual winter simulation delta breakdown | `src/ae_watch/api/services.py` | `simulate_what_if` |
| 195 | Deterministic random seed governance across folds (`random_state=42`) | `src/models/conformal_forecaster.py` | `_fit_target_conformal` |
| 196 | Empty-slice boundary protection in audit computation | `src/evaluation/error_analysis.py` | `_compute_slice_metrics` |
| 197 | Cross-hospital unseeing group validation verification | `tests/test_v2_pipeline.py` | `test_conformal_models_and_error_report` |
| 198 | Pickle bundle serialization for fast API startup | `src/models/conformal_forecaster.py` | `DEFAULT_MODEL_BUNDLE_PATH` |
| 199 | Global SHAP feature ranking Markdown export | `src/evaluation/error_analysis.py` | `generate_error_analysis_report` |
| 200 | Adaptive interval widening under winter surge heteroskedasticity | `src/evaluation/error_analysis.py` | `breach_pi_width` |

---

## Domain 5: Guardrailed Clinical RAG & Agentic AI (Skills 201–250)

| # | Capability | Implementation File | Symbol / Artifact |
| ---: | :--- | :--- | :--- |
| 201 | Disk-backed regulatory document scanner (`rglob`) | `src/agents/clinical_copilot.py` | `load_nhs_clinical_corpus` |
| 202 | PDF extraction via `pypdf.PdfReader` | `src/agents/clinical_copilot.py` | `_read_document_text` |
| 203 | Markdown & plain-text clinical document ingestion | `src/agents/clinical_copilot.py` | `_read_document_text` |
| 204 | Section-aware header & paragraph document chunking | `src/agents/clinical_copilot.py` | `load_nhs_clinical_corpus` |
| 205 | Statutory Document ID extraction (`**Document ID:**`) | `src/agents/clinical_copilot.py` | `load_nhs_clinical_corpus` |
| 206 | Statutory NHS OPEL Framework knowledge base (`OPEL 1`–`4`) | `data/regulatory_docs/nhs_opel_framework.md` | `NHS-OPEL-2024-STD` |
| 207 | Statutory NICE Guideline NG94 emergency care standards | `data/regulatory_docs/nice_ng94_emergency_acute_care.md` | `NICE-NG94-UEC` |
| 208 | Statutory RCEM Safe Staffing & Crowding standards | `data/regulatory_docs/rcem_safe_staffing_crowding.md` | `RCEM-CROWDING-2024` |
| 209 | `BM25Okapi` sparse lexical indexing (`rank-bm25`) | `src/agents/clinical_copilot.py` | `load_nhs_clinical_corpus` |
| 210 | `TfidfVectorizer` bigram/unigram cosine semantic-lexical scoring | `src/agents/clinical_copilot.py` | `ClinicalCorpusRetriever.search` |
| 211 | Reciprocal Rank Fusion (RRF, `k=60`) hybrid scoring | `src/agents/clinical_copilot.py` | `ClinicalCorpusRetriever.search` |
| 212 | Lazy-loaded + hot-reloadable corpus index wrapper | `src/agents/clinical_copilot.py` | `ClinicalCorpusRetriever` |
| 213 | Google Gemini `gemini-embedding-2` (3072-dim) unit embeddings | `src/ae_watch/rag/embeddings.py` | `GeminiEmbeddingClient` |
| 214 | PostgreSQL `pgvector` exact cosine nearest-neighbor search | `src/ae_watch/rag/vector_store.py` | `VectorStore.dense_search` |
| 215 | PostgreSQL `tsvector` + GIN index BM25 sparse search | `src/ae_watch/rag/vector_store.py` | `VectorStore.sparse_search` |
| 216 | Local HuggingFace Cross-Encoder reranking (`ms-marco-MiniLM-L-6-v2`) | `src/ae_watch/rag/hybrid_retriever.py` | `HybridRetriever` |
| 217 | 3-way RAG fusion (pgvector + BM25 + Neo4j subgraph) | `src/ae_watch/rag/hybrid_retriever.py` | `HybridRetriever.retrieve` |
| 218 | Stateful LangGraph `StateGraph` copilot workflow | `src/agents/clinical_copilot.py` | `ClinicalEscalationCopilot.build_graph` |
| 219 | Conditional LangGraph guardrail routing (`refusal` vs `retrieve`) | `src/agents/clinical_copilot.py` | `ClinicalEscalationCopilot.build_graph` |
| 220 | Input prompt-injection pattern matching engine | `src/agents/clinical_copilot.py` | `INJECTION_PATTERNS` |
| 221 | System prompt exfiltration blocking | `src/agents/clinical_copilot.py` | `input_guardrail_node` |
| 222 | Clinical policy override / bypass refusal handler | `src/agents/clinical_copilot.py` | `refusal_node` |
| 223 | Pre-LLM NHS 10-digit number sanitization | `src/agents/clinical_copilot.py` | `input_guardrail_node` |
| 224 | Pre-LLM UK postcode sanitization | `src/agents/clinical_copilot.py` | `input_guardrail_node` |
| 225 | Deterministic OPEL escalation calculation inside agent graph | `src/agents/clinical_copilot.py` | `opel_synthesis_node` |
| 226 | Dual-LLM routing (`gemini-3.5-flash-lite` + `gemini-3.8-flash`) | `src/ae_watch/agent/graph.py` | `ClinicalOperationsAgent` |
| 227 | Automated Gemini HTTP 429/503 quota fallback to deterministic SOP | `src/agents/clinical_copilot.py` | `opel_synthesis_node` |
| 228 | Citation-Verifier Judge node in LangGraph | `src/agents/clinical_copilot.py` | `citation_verifier_judge_node` |
| 229 | Mandatory Trust ODS code grounding verification | `src/agents/clinical_copilot.py` | `citation_verifier_judge_node` |
| 230 | Mandatory OPEL tier & regulatory document ID grounding verification | `src/agents/clinical_copilot.py` | `citation_verifier_judge_node` |
| 231 | Typed tool: SQL Forecast & SHAP inspector | `src/ae_watch/agent/tools.py` | `inspect_forecast_and_shap` |
| 232 | Typed tool: Causal Cold Alert impact simulator | `src/ae_watch/agent/tools.py` | `simulate_causal_cold_alert` |
| 233 | Typed tool: Hybrid clinical policy retriever | `src/ae_watch/agent/tools.py` | `retrieve_hybrid_clinical_policy` |
| 234 | Automated RAG & safety benchmark harness (10 scenarios) | `src/ae_watch/eval/benchmark.py` | `SafetyAndRAGBenchmark` |
| 235 | Retrieval Top-3 Hit Rate automated scoring (`100%`) | `docs/safety_rag_benchmark.json` | `retrieval_hit_rate` |
| 236 | Adversarial Refusal Accuracy automated scoring (`100%`) | `docs/safety_rag_benchmark.json` | `refusal_accuracy` |
| 237 | Patient PII Redaction Recall automated scoring (`100%`) | `docs/safety_rag_benchmark.json` | `pii_redaction_recall` |
| 238 | Alphanumeric lexical tokenization for medical acronyms | `src/agents/clinical_copilot.py` | `_tokenize` |
| 239 | Empty / missing regulatory directory explicit `FileNotFoundError` | `src/agents/clinical_copilot.py` | `load_nhs_clinical_corpus` |
| 240 | DuckDB telemetry injection into agent prompt context | `src/agents/clinical_copilot.py` | `_fetch_latest_duckdb_telemetry` |
| 241 | Degraded telemetry fallback inside agent workflow | `src/agents/clinical_copilot.py` | `_fetch_latest_duckdb_telemetry` |
| 242 | UI citation badge display & safety verification indicators | `src/app/dashboard.py` | `st.caption` |
| 243 | 45-minute ambulance handover SOP retrieval grounding | `data/regulatory_docs/rcem_safe_staffing_crowding.md` | `RCEM-CROWDING-2024` |
| 244 | SDEC 12-hour/7-day ambulatory standard grounding | `data/regulatory_docs/nice_ng94_emergency_acute_care.md` | `NICE-NG94-UEC` |
| 245 | Virtual Ward 80%+ step-down trigger grounding | `data/regulatory_docs/nhs_opel_framework.md` | `NHS-OPEL-2024-STD` |
| 246 | FastAPI OpenAPI typed Copilot request/response contract | `src/app/main.py` | `CopilotRequest`, `CopilotResponse` |
| 247 | Deterministic LLM timeout deadline validation (`10000ms`) | `src/agents/clinical_copilot.py` | `types.HttpOptions` |
| 248 | Unit test verification of PDF parsing via `pypdf` | `tests/test_v2_pipeline.py` | `test_load_nhs_clinical_corpus_markdown_txt_and_pdf` |
| 249 | Unit test verification of citation judge grounding | `tests/test_v2_pipeline.py` | `test_langgraph_opel_copilot_pii_and_citations` |
| 250 | Benchmark JSON & Markdown report generation | `src/ae_watch/eval/benchmark.py` | `docs/safety_rag_benchmark.md` |

---

## Domain 6: MLOps, Cloud IaC & Production Delivery (Skills 251–300)

| # | Capability | Implementation File | Symbol / Artifact |
| ---: | :--- | :--- | :--- |
| 251 | Unified `src.run_pipeline` module orchestration (`python -m`) | `src/run_pipeline.py` | `run_pipeline` |
| 252 | FastAPI v2 REST service with CORS & correlation tracing | `src/app/main.py` | `app` |
| 253 | FastAPI `/health` multi-subsystem readiness probe | `src/app/main.py` | `get_health` |
| 254 | FastAPI `/api/v1/trusts/{ods_code}/telemetry` endpoint | `src/app/main.py` | `get_trust_telemetry_and_conformal` |
| 255 | FastAPI `/api/v1/copilot/ask` guarded agent endpoint | `src/app/main.py` | `post_copilot_ask` |
| 256 | FastAPI v1 full clinical gateway (`simulate/what-if`, `forecast`) | `src/ae_watch/api/app.py` | `app` |
| 257 | Streamlit v2 clinical-ops command centre UI | `src/app/dashboard.py` | `main` |
| 258 | Streamlit v1 geospatial simulator command centre UI | `src/ae_watch/dashboard/app.py` | `ae_watch.dashboard.app` |
| 259 | Degraded-feed resilient UI operation without running API daemon | `src/app/dashboard.py` | `fetch_api_telemetry` |
| 260 | Root production multi-service `Dockerfile` (`python:3.12-slim`) | `Dockerfile` | `Dockerfile` |
| 261 | Local Docker Compose orchestrating Postgres, Neo4j, Marquez, MLflow, API | `docker-compose.yml` | `docker-compose.yml` |
| 262 | Containerized MLflow tracking server backed by SQLite | `docker-compose.yml` | `mlflow` service (`5005`) |
| 263 | Containerized FastAPI container healthchecks via `curl` | `docker-compose.yml` | `api` service (`8000`) |
| 264 | Deterministic dependency locking via `uv` & `uv.lock` | `pyproject.toml`, `uv.lock` | `uv sync --frozen` |
| 265 | Editable & src-layout pytest pythonpath configuration | `pyproject.toml` | `[tool.pytest.ini_options]` |
| 266 | Modular Terraform AWS VPC & multi-AZ subnet architecture | `infra/terraform/modules/networking/main.tf` | `aws_vpc.main` |
| 267 | Modular Terraform RDS PostgreSQL 16 + pgvector parameter group | `infra/terraform/modules/database/main.tf` | `aws_db_instance.postgres` |
| 268 | Modular Terraform ECS Fargate + ALB compute stack | `infra/terraform/modules/compute/main.tf` | `aws_ecs_cluster.main` |
| 269 | Modular Terraform IAM & Secrets Manager security module | `infra/terraform/modules/security/main.tf` | `aws_iam_role.ecs_execution_role` |
| 270 | Automated Terraform HCL brace/quote & tag verification tests | `tests/test_terraform.py` | `test_terraform_hcl_syntax_validation` |
| 271 | GitHub Actions CI workflow automating quality, dbt, pipeline & pytest | `.github/workflows/ci.yml` | `quality-and-tests` |
| 272 | Automated Ruff lint check across `src` and `tests` | `.github/workflows/ci.yml` | `uv run ruff check src tests` |
| 273 | Automated Ruff formatting verification | `.github/workflows/ci.yml` | `uv run ruff format --check src tests` |
| 274 | Automated `dbt parse` manifest validation in CI | `.github/workflows/ci.yml` | `dbt parse` |
| 275 | Automated offline `--no-live` pipeline smoke test in CI | `.github/workflows/ci.yml` | `uv run python -m src.run_pipeline --no-live` |
| 276 | Mocked httpx connector unit tests with `LIVE_NHS_FEED_DEGRADED` | `tests/test_v2_pipeline.py` | `test_live_nhs_connector_degraded_fallback` |
| 277 | Pandera quarantine & GDPR hashing unit test suite | `tests/test_v2_pipeline.py` | `test_pandera_quarantine_and_gdpr_pseudonymisation` |
| 278 | FastAPI TestClient endpoint & correlation header tests | `tests/test_v2_pipeline.py` | `test_v2_fastapi_endpoints` |
| 279 | Structured key-value operational logging via `structlog` | `src/ae_watch/utils/logger.py` | `logger` |
| 280 | High-resolution LinkedIn / portfolio showcase visual generator | `scripts/generate_linkedin_visuals.py` | `create_image_1_command_centre` |
| 281 | Environment variable schema validation via `pydantic-settings` | `src/ae_watch/config.py` | `Settings` |
| 282 | Cross-platform OpenMP/MLflow safety environment guards | `tests/conftest.py` | `OMP_NUM_THREADS`, `MLFLOW_DISABLE_AGENT_HINT` |
| 283 | Zero-leakage error response testing (no `Traceback` in HTTP 422) | `tests/test_api.py` | `test_api_validation_error_structure_no_leakage` |
| 284 | Resilient HTTP mocking via `respx` in ingestion unit tests | `tests/test_resilience.py` | `test_resilience_recovers_from_429` |
| 285 | Data-contract integration verification against Postgres views | `tests/test_dbt_contracts.py` | `test_silver_nhs_ae_contracts` |
| 286 | Interactive What-If causal simulation contract testing | `tests/test_api.py` | `test_api_what_if_simulation_endpoint` |
| 287 | Gitignore protection allowing statutory docs while hiding DB binaries | `.gitignore` | `!data/regulatory_docs/**` |
| 288 | Reproducible database schema + seed dump initialization | `infra/init-scripts/` | `01_init_db.sql`, `02_seed_data.sql.gz` |
| 289 | Clean Hatchling wheel build target across all v1 & v2 packages | `pyproject.toml` | `[tool.hatch.build.targets.wheel]` |
| 290 | Expander integration of error analysis report inside Streamlit UI | `src/app/dashboard.py` | `st.expander` |
| 291 | Automated MLflow experiment creation (`ae_watch_uk_v2_conformal`) | `src/models/conformal_forecaster.py` | `mlflow.set_experiment` |
| 292 | Cross-version Python >=3.11 / 3.12 compatibility enforcement | `pyproject.toml` | `requires-python = ">=3.11"` |
| 293 | Reciprocal Rank Fusion multi-retriever modular extensibility | `src/agents/clinical_copilot.py` | `ClinicalCorpusRetriever` |
| 294 | End-to-end headless UI browser verification pattern | `tests/test_v2_pipeline.py` | Dashboard & API smoke checks |
| 295 | Multi-endpoint alias routing (`/api/v1/copilot/ask` & `/api/v1/agent/query`) | `src/app/main.py` | `post_copilot_ask` |
| 296 | Dual v1 Postgres/Neo4j + v2 DuckDB/MAPIE architectural coexistence | `src/ae_watch/` + `src/` | Preserved backward compatibility |
| 297 | Pre-commit style and lint parity between local and CI runners | `pyproject.toml` | `[tool.ruff]` |
| 298 | Automated repository attribution & license documentation | `README.md` | Author `CHRISH PEP FELIX A` |
| 299 | Zero-cost (`£0 / $0`) fully open-source operational stack | `pyproject.toml` | Open-Meteo, UKHSA, DuckDB, LightGBM, MAPIE |
| 300 | Full-lifecycle CI/CD verification from ingestion to copilot citations | `.github/workflows/ci.yml` | `AE-Watch UK CI Pipeline` |
