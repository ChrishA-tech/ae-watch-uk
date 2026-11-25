"""FastAPI v2 Service Gateway for AE-Watch UK (DuckDB + MAPIE Conformal + OPEL Copilot).

Provides resilient health checks, Trust telemetry & conformal forecasts, and guarded
LangGraph OPEL escalation copilot endpoints with automatic LIVE_NHS_FEED_DEGRADED fallback.

Author: CHRISH PEP FELIX A
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import structlog
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.agents.clinical_copilot import (
    calculate_opel_tier,
    clinical_copilot,
)
from src.ingestion.ae_pipeline import (
    DEFAULT_DUCKDB_PATH,
    apply_uk_gdpr_pseudonymisation,
)
from src.ingestion.live_nhs_connectors import fetch_live_nhs_and_weather_telemetry
from src.models.conformal_forecaster import (
    DEFAULT_MODEL_BUNDLE_PATH,
    predict_trust_conformal,
)

logger = structlog.get_logger("ae_watch.v2.api")

app = FastAPI(
    title="AE-Watch UK v2 Clinical Escalation & Conformal Forecasting API",
    version="2.0.0",
    description="NHS Urgent & Emergency Care Conformal ML and Guarded OPEL Copilot. Author: CHRISH PEP FELIX A",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_middleware(request: Request, call_next: Any) -> Response:
    """Propagate or generate X-Correlation-ID on every request."""
    corr_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.correlation_id = corr_id
    resp: Response = await call_next(request)
    resp.headers["X-Correlation-ID"] = corr_id
    return resp


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return structured validation errors with zero stack trace leakage."""
    corr_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": "Invalid API request payload.",
            "correlation_id": corr_id,
            "details": exc.errors(),
        },
        headers={"X-Correlation-ID": corr_id},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return safe HTTP 503 without leaking internal Python tracebacks."""
    corr_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    logger.error("api_v2_unhandled_error", correlation_id=corr_id, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error_code": "SERVICE_DEGRADED",
            "message": "Service temporarily degraded; please reference correlation_id.",
            "correlation_id": corr_id,
        },
        headers={"X-Correlation-ID": corr_id},
    )


class CopilotRequest(BaseModel):
    """Request schema for the OPEL Escalation Copilot."""

    query: str = Field(..., min_length=3, max_length=1000)
    trust_ods_code: str = Field("REM", min_length=3, max_length=5)


class CopilotResponse(BaseModel):
    """Response schema for the OPEL Escalation Copilot."""

    trust_ods_code: str
    opel_assessment: dict[str, Any]
    response: str
    citations: list[str]
    citation_verified: bool
    pii_detected: bool
    is_injection: bool
    correlation_id: str


def _load_trust_latest_row(ods_code: str) -> tuple[pd.DataFrame, str]:
    """Load latest Trust telemetry from DuckDB, falling back cleanly if unavailable."""
    ods = ods_code.upper()
    if DEFAULT_DUCKDB_PATH.exists():
        try:
            with duckdb.connect(str(DEFAULT_DUCKDB_PATH), read_only=True) as conn:
                df = conn.execute(
                    """
                    SELECT * FROM trust_sitrep_daily
                    WHERE trust_ods_code = ?
                    ORDER BY observation_date DESC
                    LIMIT 1
                    """,
                    [ods],
                ).df()
            if not df.empty:
                return df, str(df["feed_status"].iloc[0])
        except Exception as exc:  # noqa: BLE001
            logger.warning("duckdb_api_fallback", error=str(exc), ods=ods)

    fallback_df = fetch_live_nhs_and_weather_telemetry(live=False)
    fallback_df = apply_uk_gdpr_pseudonymisation(fallback_df)
    sub = fallback_df[fallback_df["trust_ods_code"] == ods]
    if sub.empty:
        sub = fallback_df.head(1).copy()
        sub["trust_ods_code"] = ods
    return sub, "LIVE_NHS_FEED_DEGRADED"


@app.get("/health", tags=["System"])
async def get_health() -> dict[str, Any]:
    """Check DuckDB, MLflow SQLite, MAPIE bundle, and regulatory corpus readiness."""
    duckdb_ready = DEFAULT_DUCKDB_PATH.exists()
    mlflow_ready = Path("mlruns/mlflow.db").exists()
    model_ready = DEFAULT_MODEL_BUNDLE_PATH.exists()
    docs_ready = Path("data/regulatory_docs/nhs_opel_framework.md").exists()

    return {
        "status": "healthy" if (duckdb_ready and model_ready and docs_ready) else "degraded",
        "version": "2.0.0",
        "author": "CHRISH PEP FELIX A",
        "subsystems": {
            "duckdb": "ready" if duckdb_ready else "fallback_mode",
            "mlflow_sqlite": "ready" if mlflow_ready else "not_initialized",
            "conformal_models": "ready" if model_ready else "fallback_analytic",
            "regulatory_corpus": "ready" if docs_ready else "missing",
        },
    }


@app.get("/api/v1/trusts/{ods_code}/telemetry", tags=["Telemetry & Conformal ML"])
async def get_trust_telemetry_and_conformal(ods_code: str = "REM") -> dict[str, Any]:
    """Return latest Trust SitRep metrics, OPEL tier, and MAPIE 90% conformal intervals."""
    df_row, feed_status = _load_trust_latest_row(ods_code)
    rec = df_row.iloc[0].to_dict()

    opel = calculate_opel_tier(
        four_hour_compliance_ratio=float(rec["four_hour_compliance_ratio"]),
        bed_occupancy_ratio=float(rec["bed_occupancy_ratio"]),
        twelve_hour_trolley_waits=int(rec["twelve_hour_trolley_waits"]),
        cold_snap_trigger=int(rec["cold_snap_trigger"]),
    )

    if DEFAULT_MODEL_BUNDLE_PATH.exists():
        conformal_pred = predict_trust_conformal(df_row)
    else:
        breach_pt = round(float(rec["four_hour_breach_rate_pct"]), 2)
        trolley_pt = float(rec["twelve_hour_trolley_waits"])
        conformal_pred = {
            "breach_rate_pct": {
                "point": breach_pt,
                "pi90_lower": round(max(0.0, breach_pt - 4.5), 2),
                "pi90_upper": round(min(100.0, breach_pt + 4.5), 2),
            },
            "twelve_hour_trolley_waits": {
                "point": trolley_pt,
                "pi90_lower": round(max(0.0, trolley_pt - 12.0), 1),
                "pi90_upper": round(trolley_pt + 12.0, 1),
            },
            "shap_top_drivers": [],
        }

    return {
        "trust_ods_code": str(rec["trust_ods_code"]),
        "trust_name": str(rec["trust_name"]),
        "region": str(rec["region"]),
        "trust_type": str(rec["trust_type"]),
        "observation_date": str(rec["observation_date"]),
        "feed_status": feed_status,
        "opel_assessment": opel,
        "conformal_forecast_90ci": conformal_pred,
        "weather_and_pathogens": {
            "temp_c": float(rec["temp_c"]),
            "min_temp_c": float(rec["min_temp_c"]),
            "cold_snap_trigger": int(rec["cold_snap_trigger"]),
            "ukhsa_flu_admission_rate": float(rec["ukhsa_flu_admission_rate"]),
            "ukhsa_rsv_admission_rate": float(rec["ukhsa_rsv_admission_rate"]),
        },
    }


@app.post("/api/v1/copilot/ask", response_model=CopilotResponse, tags=["Clinical Copilot"])
@app.post("/api/v1/agent/query", response_model=CopilotResponse, tags=["Clinical Copilot"])
async def post_copilot_ask(req: CopilotRequest, request: Request) -> CopilotResponse:
    """Invoke guarded LangGraph OPEL Clinical Escalation Copilot."""
    corr_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    out = clinical_copilot.ask(query=req.query, trust_ods_code=req.trust_ods_code)
    return CopilotResponse(
        trust_ods_code=req.trust_ods_code.upper(),
        opel_assessment=out.get("opel_assessment", {}),
        response=out.get("final_response", ""),
        citations=out.get("citations", []),
        citation_verified=bool(out.get("citation_verified", False)),
        pii_detected=bool(out.get("pii_detected", False)),
        is_injection=bool(out.get("is_injection", False)),
        correlation_id=corr_id,
    )
