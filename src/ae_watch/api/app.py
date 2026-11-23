"""FastAPI Application for AE-Watch UK Clinical-Ops Gateway.

Author: CHRISH PEP FELIX A
Project: AE-Watch UK
"""

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ae_watch.api.schemas import (
    AgentQueryRequest,
    AgentQueryResponse,
    ErrorResponse,
    HealthResponse,
    TrustForecastResponse,
    WhatIfRequest,
    WhatIfResponse,
)
from ae_watch.api.services import (
    check_health,
    execute_agent_query,
    get_trust_forecast,
    simulate_what_if,
)
from ae_watch.utils.logger import logger

app = FastAPI(
    title="AE-Watch UK Clinical-Ops Gateway",
    version="1.0.0",
    description="Inference and Clinical Agent API for NHS Winter Pressure & A&E Surge Management. Author: CHRISH PEP FELIX A",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 1. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 2. Correlation ID Middleware
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next: Any) -> Response:
    """Attach or propagate unique tracing correlation ID on every HTTP transaction."""
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id

    response: Response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


# 3. Exception Handlers (Guaranteed zero raw stack trace leakage)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return structured HTTP 422 validation error with field diagnostics."""
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    logger.warning("api_validation_error", correlation_id=correlation_id, errors=exc.errors())
    payload = ErrorResponse(
        error_code="VALIDATION_ERROR",
        message="Request payload failed Pydantic schema validation.",
        correlation_id=correlation_id,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details=exc.errors(),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=payload.model_dump(),
        headers={"X-Correlation-ID": correlation_id},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Return structured HTTP error."""
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    payload = ErrorResponse(
        error_code="HTTP_ERROR",
        message=str(exc.detail),
        correlation_id=correlation_id,
        status_code=exc.status_code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=payload.model_dump(),
        headers={"X-Correlation-ID": correlation_id},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all unhandled exceptions returning clean HTTP 503 without leaking stack traces."""
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    logger.error("api_unhandled_system_error", correlation_id=correlation_id, error=str(exc))
    payload = ErrorResponse(
        error_code="SYSTEM_UNAVAILABLE",
        message="An unexpected system error occurred. Please reference the correlation ID with clinical-ops support.",
        correlation_id=correlation_id,
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=payload.model_dump(),
        headers={"X-Correlation-ID": correlation_id},
    )


# 4. API Endpoints
@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health and Readiness Probe",
    tags=["System"],
)
async def get_health() -> HealthResponse:
    """Verify health of PostgreSQL, Neo4j, and MLflow artifacts."""
    return check_health()


@app.get(
    "/api/v1/trusts/{ods_code}/forecast",
    response_model=TrustForecastResponse,
    summary="Multi-Horizon Forecast and TreeSHAP Drivers",
    tags=["Forecasts"],
)
async def get_forecast(ods_code: str = "REM") -> TrustForecastResponse:
    """Fetch 7d and 14d P10/P50/P90 breach forecasts, TreeSHAP drivers, and 25 km catchment metrics."""
    return get_trust_forecast(ods_code)


@app.post(
    "/api/v1/simulate/what-if",
    response_model=WhatIfResponse,
    summary="Winter Surge What-If Causal Simulation",
    tags=["Simulation"],
)
async def post_simulate_what_if(req: WhatIfRequest) -> WhatIfResponse:
    """Simulate winter surge scenarios using DoWhy DiD Cold Alert causal effect and SDEC mitigations."""
    return simulate_what_if(req)


@app.post(
    "/api/v1/agent/query",
    response_model=AgentQueryResponse,
    summary="Clinical-Ops Agent Inquiry",
    tags=["Clinical Agent"],
)
async def post_agent_query(req: AgentQueryRequest, request: Request) -> AgentQueryResponse:
    """Execute LangGraph clinical-ops agent query with safety guardrails and policy citations."""
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    return execute_agent_query(req, correlation_id)
