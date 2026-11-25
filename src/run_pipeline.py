"""AE-Watch UK v2 End-to-End Pipeline Runner.

Supports --live / --no-live (argparse.BooleanOptionalAction, defaulting to True).
Executes: Live UK Connectors -> Pandera Quarantine & UK GDPR -> DuckDB ->
GroupKFold LightGBM+MAPIE Conformal ML -> MLflow SQLite -> Sliced Error Report -> Clinical RAG Check.

Author: CHRISH PEP FELIX A
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import structlog

from src.agents.clinical_copilot import load_nhs_clinical_corpus
from src.evaluation.error_analysis import generate_error_analysis_report
from src.ingestion.ae_pipeline import run_ae_ingestion_pipeline
from src.models.conformal_forecaster import train_conformal_ae_models

logger = structlog.get_logger("ae_watch.v2.runner")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments with BooleanOptionalAction for --live / --no-live."""
    parser = argparse.ArgumentParser(
        description="Run AE-Watch UK v2 end-to-end urgent care pipeline."
    )
    parser.add_argument(
        "--live",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fetch live Open-Meteo & UKHSA feeds (use --no-live for degraded fallback baseline).",
    )
    return parser.parse_args(argv)


def run_pipeline(live: bool = True) -> dict[str, Any]:
    """Execute complete AE-Watch UK v2 production pipeline."""
    logger.info("pipeline_v2_started", live=live)

    # 1. Ingestion, Pandera Validation, Parquet Quarantine, UK GDPR Pseudonymisation, DuckDB
    ingestion_res = run_ae_ingestion_pipeline(live=live)

    # 2. Trust-Grouped (GroupKFold) LightGBM + MAPIE 90% Conformal ML + MLflow SQLite
    model_res = train_conformal_ae_models(ingestion_res["df"])

    # 3. Sliced Error Analysis Report (docs/ERROR_ANALYSIS_REPORT.md)
    report_res = generate_error_analysis_report(
        model_res["eval_df"],
        shap_importance=model_res["shap_importance"],
    )

    # 4. Verify Disk-Backed Clinical Regulatory RAG Index
    corpus_res = load_nhs_clinical_corpus(Path("data/regulatory_docs"))

    summary = {
        "status": "completed",
        "live_mode": live,
        "feed_status": ingestion_res["feed_status"],
        "valid_rows": ingestion_res["valid_rows"],
        "quarantined_rows": ingestion_res["quarantined_rows"],
        "duckdb_path": ingestion_res["duckdb_path"],
        "metrics": model_res["metrics"],
        "mlflow_run_id": model_res["mlflow_run_id"],
        "error_analysis_report": report_res["report_path"],
        "clinical_corpus_files": corpus_res["files"],
        "clinical_corpus_chunks": len(corpus_res["chunks"]),
    }
    logger.info("pipeline_v2_completed", **summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = parse_args(argv)
    summary = run_pipeline(live=args.live)
    print(
        f"[AE-Watch UK v2] Completed | feed={summary['feed_status']} | "
        f"rows={summary['valid_rows']} | 4h_breach_cov90={summary['metrics']['breach_coverage_90']:.2%} | "
        f"report={summary['error_analysis_report']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
