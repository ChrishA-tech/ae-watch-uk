# Master Engineering Prompt: AE-Watch UK (NHS Winter Pressure & A&E Surge Early-Warning System)

Act as a Principal Data Scientist, Staff Data Engineer, and Lead AI Architect. Build a production-grade, end-to-end Data Science, Data Engineering, and Agentic AI project titled **AE-Watch UK**, authored by **CHRISH PEP FELIX A**, running on a **£0 / $0 infrastructure budget**.

## 1. Core Mandate, Authorship & Zero-Cost Constraints
- **Author Attribution:** Credit **CHRISH PEP FELIX A** in `pyproject.toml`, `LICENSE` (MIT), `README.md`, FastAPI OpenAPI metadata, OpenLineage producer metadata, and the interactive dashboard footer.
- **Zero Synthetic Data:** Every metric, time series, Trust code, and clinical protocol must be ingested from real, publicly accessible UK sources:
  1. **NHS England A&E Attendances & Emergency Admissions:** Monthly and weekly Trust-level attendances, 4-hour performance percentages, and >12-hour trolley waits mapped by official NHS Organisation Data Service (ODS) Trust codes (explicitly benchmarking **Liverpool University Hospitals NHS Foundation Trust** — ODS code `REM`, plus neighboring Cheshire & Merseyside ICB Trusts).
  2. **UK Health Security Agency (UKHSA) Data Dashboard REST API (`https://api.ukhsa-dashboard.data.gov.uk`):** Weekly regional and national laboratory reports for Norovirus, Influenza, and RSV.
  3. **Meteorological Telemetry (Open-Meteo Historical & Forecast Archive API `https://api.open-meteo.com`):** Daily minimum/mean temperature, wind chill, frost days, and cold-snap degree-days mapped to the latitude/longitude of each NHS Trust's primary hospital site.
  4. **NHS Operational Guidance Corpus (for GraphRAG):** Official public NHS England *Urgent and Emergency Care (UEC) Recovery Plan* and *Winter Resilience* operational guidance documents.
- **£0 Free-Tier LLM & Local Compute Rules:**
  - Read `GEMINI_API_KEY`, `GEMINI_REASONING_MODEL` (`gemini-3.8-flash`), `GEMINI_FAST_MODEL` (`gemini-3.5-flash-lite`), and `GEMINI_EMBEDDING_MODEL` (`gemini-embedding-2`) from `.env` using the official `google-genai` Python SDK.
  - Do **not** call paid-only models (such as `gemini-3.1-pro-preview` or `gemini-4-argon`).
  - Include exponential backoff retry logic (`tenacity`) for HTTP `429` Free-Tier rate limits and semantic response caching in Redis/SQLite to minimize API calls.
  - Run all databases, lineage servers, ML training (Apple Silicon MPS / CPU), and experiment tracking locally via Docker Compose.

## 2. Repository Structure to Generate
Create a clean, modular monorepo with working code, configuration, and tests in every directory:

```text
ae-watch-uk/
├── .github/workflows/
│   └── ci.yml                      # Ruff, Mypy, Pytest, dbt test, RAGAS eval gate
├── data/                           # Git-ignored local Bronze/Silver/Gold Parquet & DuckDB
├── dbt_ae_watch/                   # dbt project (models, snapshots, schema.yml tests)
│   ├── dbt_project.yml
│   ├── models/
│   │   ├── staging/                # Bronze -> Silver cleaning & ODS Trust standardization
│   │   ├── intermediate/           # Spatial joins, cold-snap degree days, lagged UKHSA rates
│   │   └── marts/                  # Gold ML feature store & causal inference panels
│   └── tests/                      # Custom SQL data contract tests
├── infra/terraform/                # Modular Terraform IaC (Object Storage, Postgres, Container Hosting)
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── src/ae_watch/
│   ├── __init__.py
│   ├── config.py                   # Pydantic Settings & .env validation
│   ├── ingestion/
│   │   ├── nhs_ae_loader.py        # AsyncIO NHS England A&E CSV/API fetcher + Pandera contracts
│   │   ├── ukhsa_client.py         # UKHSA Data Dashboard REST API client
│   │   ├── weather_client.py       # Open-Meteo Trust-coordinate weather & cold-alert calculator
│   │   └── lineage.py              # OpenLineage / Marquez event emitter (START/COMPLETE/FAIL)
│   ├── features/
│   │   ├── spatial.py              # GeoPandas, H3 hexagonal indexing, neighboring Trust spillover
│   │   └── temporal.py             # Fourier seasonal terms, rolling windows, epidemiological lags
│   ├── models/
│   │   ├── train_gbdt.py           # LightGBM, XGBoost, CatBoost + Optuna + Quantile intervals
│   │   ├── train_tft.py            # PyTorch Temporal Fusion Transformer (multi-horizon)
│   │   ├── causal_impact.py        # DoWhy Difference-in-Differences on UKHSA Cold Health Alerts
│   │   └── explainability.py       # TreeSHAP driver extraction & Brier probability calibration
│   ├── agents/
│   │   ├── graph_builder.py        # Neo4j Cypher loader (Trusts -> ICBs -> Escalation Protocols)
│   │   ├── hybrid_retriever.py     # pgvector dense + BM25 sparse + Cross-Encoder reranking
│   │   ├── copilot_graph.py        # LangGraph supervisor-worker state machine (Free-Tier Gemini)
│   │   └── guardrails.py           # Prompt-injection filter, Presidio PII check, citation grounding
│   ├── api/
│   │   └── main.py                 # FastAPI service (/predict, /explain, /copilot, /health, /metrics)
│   └── monitoring/
│       └── drift.py                # Evidently AI data/concept drift & PSI report generator
├── evals/
│   └── run_ragas.py                # Automated RAGAS (Faithfulness, Answer Relevancy, Context Recall)
├── dashboard/
│   └── app.py                      # Interactive UK Trust map, SHAP breakdown, what-if simulator & Copilot
├── tests/
│   ├── test_ingestion.py
│   ├── test_features.py
│   ├── test_models.py
│   └── test_api.py
├── docker-compose.yml              # Postgres+PostGIS+pgvector, Neo4j, Marquez, MLflow, Prometheus, Grafana
├── Dockerfile
├── pyproject.toml                  # uv / Poetry dependencies, Ruff & Mypy strict rules
└── README.md                       # Architecture diagram, benchmark table, setup guide under CHRISH PEP FELIX A
```

## 3. Step-by-Step Execution Phases
Execute the build sequentially across 5 verified phases, pausing to verify tests and terminal outputs after each phase:

1. **Phase 1 — Infrastructure, Medallion Ingestion & Lineage (`src/ae_watch/ingestion/` & `dbt_ae_watch/`):**
   - Write `docker-compose.yml` running PostgreSQL 16 (with `postgis` and `vector` extensions), Neo4j Community, MLflow, and Marquez (OpenLineage backend).
   - Build asynchronous ingestion scripts using `httpx`, `tenacity` retries, and `Polars` to pull real historical NHS England A&E Trust data, UKHSA Norovirus/Influenza/RSV metrics, and Open-Meteo weather telemetry for NHS England Trusts.
   - Enforce `Pandera` data contracts at the Bronze boundary and emit OpenLineage run events into Marquez.
   - Build `dbt` models transforming Bronze tables into Silver standardized Trust records and Gold ML feature marts, verified with `dbt test` and `pytest`.

2. **Phase 2 — Geospatial Features, Multi-Horizon Forecasting & Causal Inference (`src/ae_watch/features/` & `src/ae_watch/models/`):**
   - Implement `spatial.py` with `GeoPandas` and `h3` hexagonal indexing to compute catchment overlap and neighboring Trust surge spillover signals.
   - Implement `train_gbdt.py` (LightGBM, XGBoost, CatBoost with `Optuna` hyperparameter tuning and expanding-window walk-forward CV) predicting 7-day and 14-day Trust A&E 4-hour breach rates with 10th/50th/90th quantile prediction intervals.
   - Implement `train_tft.py` in `PyTorch` (Temporal Fusion Transformer supporting Apple Silicon MPS and CPU) and log all metrics (MAE, RMSE, sMAPE, Pinball Loss, Brier Score) and TreeSHAP artifacts to `MLflow`.
   - Implement `causal_impact.py` using `DoWhy` Difference-in-Differences to isolate the causal impact of cold-weather alert thresholds on Trust breach performance.

3. **Phase 3 — Agentic GraphRAG Copilot & AI Safety (`src/ae_watch/agents/` & `evals/`):**
   - Populate `Neo4j` via `graph_builder.py` with nodes and relationships linking `Trust`, `ICB`, `RiskLevel`, and `EscalationProtocol`.
   - Implement `hybrid_retriever.py` combining `pgvector` (`gemini-embedding-2`) dense search, BM25 sparse retrieval, and Cross-Encoder reranking (`BAAI/bge-reranker-base`).
   - Build `copilot_graph.py` in `LangGraph` using `gemini-3.8-flash` (reasoning/synthesis) and `gemini-3.5-flash-lite` (intent routing/guardrails) with nodes: `classify_intent` -> `fetch_trust_forecast_sql` -> `retrieve_graph_and_protocols` -> `draft_operational_plan` -> `verify_guardrails`.
   - Implement `evals/run_ragas.py` with rate-limit pacing to benchmark faithfulness and context recall on realistic NHS operational queries.

4. **Phase 4 — FastAPI Serving, Drift Observability & Terraform IaC (`src/ae_watch/api/`, `monitoring/`, `infra/`):**
   - Expose typed REST endpoints in `FastAPI` with Pydantic v2 schemas, local caching, structured JSON logging, and `/metrics` for `Prometheus`.
   - Implement `monitoring/drift.py` using `Evidently AI` to detect feature distribution drift (PSI / KS-test) between baseline winters and incoming feeds.
   - Write modular `Terraform` files in `infra/terraform/` provisioning cloud object storage, managed PostgreSQL, and containerized API hosting.

5. **Phase 5 — Decision Intelligence Dashboard & CI/CD (`dashboard/app.py` & `.github/workflows/ci.yml`):**
   - Build an interactive executive UI showing a UK map of NHS Trusts colored by predicted breach risk, top TreeSHAP drivers per Trust, interactive what-if simulation sliders ("Simulate -4°C temperature drop" or "+25% Norovirus incidence"), and the grounded LangGraph Ops Copilot panel.
   - Configure `.github/workflows/ci.yml` to run `ruff check`, `mypy`, `pytest`, and `dbt test` on every commit, and generate a portfolio-grade `README.md` with reproducible setup commands and real benchmark metrics for Liverpool University Hospitals NHS Foundation Trust (`REM`).