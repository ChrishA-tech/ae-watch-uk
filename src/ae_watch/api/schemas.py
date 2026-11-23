"""Pydantic v2 Schemas for AE-Watch UK Clinical-Ops Gateway.

Author: CHRISH PEP FELIX A
Project: AE-Watch UK
"""

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(..., description="Overall gateway operational status")
    version: str = Field("1.0.0", description="API version")
    author: str = Field("CHRISH PEP FELIX A", description="System author attribution")
    services: dict[str, str] = Field(..., description="Status of dependent downstream engines")


class ShapDriver(BaseModel):
    """TreeSHAP local feature attribution driver."""

    feature: str = Field(..., description="Feature identifier")
    importance: str = Field(..., description="Impact delta on predicted breach rate")
    description: str = Field(..., description="Clinical interpretation of the feature driver")


class CatchmentNeighbor(BaseModel):
    """Catchment trust within 25 km spillover radius."""

    neighbor_code: str = Field(..., description="ODS code of neighboring trust")
    neighbor_name: str = Field(..., description="Hospital trust name")
    distance_km: float = Field(..., description="Euclidean/Haversine distance in kilometres")
    neighbor_breach: float | None = Field(None, description="Neighboring 4-hour breach rate %")
    neighbor_opel: int | None = Field(None, description="Current OPEL escalation tier")


class QuantileForecast(BaseModel):
    """Quantile forecast bounds enforcing P10 <= P50 <= P90."""

    horizon_days: int = Field(..., description="Forecast horizon in days (7 or 14)")
    p10: float = Field(..., description="10th percentile (optimistic) breach rate %")
    p50: float = Field(..., description="50th percentile (median) breach rate %")
    p90: float = Field(..., description="90th percentile (pessimistic / surge) breach rate %")
    predicted_surge: bool = Field(..., description="Binary surge alert (breach rate >= 30%)")


class TrustForecastResponse(BaseModel):
    """Forecast and catchment risk payload for an NHS Trust."""

    trust_code: str = Field(..., description="NHS Trust ODS code (e.g. REM)")
    trust_name: str = Field(..., description="Official trust name")
    icb_code: str = Field("QE1", description="Integrated Care Board code")
    latest_observation_date: str = Field(..., description="Latest verified NHS data period")
    latest_breach_rate_pct: float = Field(..., description="Latest actual 4-hour breach rate %")
    monthly_attendances: int = Field(..., description="Latest monthly attendance volume")
    forecast_7d: QuantileForecast = Field(..., description="7-day multi-horizon breach forecast")
    forecast_14d: QuantileForecast = Field(..., description="14-day multi-horizon breach forecast")
    idw_neighbor_breach_rate: float = Field(
        ..., description="Inverse-distance-weighted peer breach rate %"
    )
    cold_snap_degree_days: float = Field(..., description="Rolling cold-snap degree days")
    shap_top_drivers: list[ShapDriver] = Field(
        ..., description="Local TreeSHAP feature attributions"
    )
    catchment_neighbors_25km: list[CatchmentNeighbor] = Field(
        ..., description="Peer acute trusts in 25 km catchment"
    )


class WhatIfRequest(BaseModel):
    """Winter surge what-if simulation request payload."""

    trust_code: str = Field("REM", description="Target NHS Trust ODS code", max_length=10)
    cold_alert_level: str = Field(
        "Amber", description="UKHSA Cold Health Alert level: Green, Yellow, Amber, Red"
    )
    norovirus_flu_surge_pct: float = Field(
        0.0, ge=0.0, le=100.0, description="Hypothesized pathogen surge increase % (0-100)"
    )
    sdec_diversion_capacity_pct: float = Field(
        0.0, ge=0.0, le=50.0, description="Same Day Emergency Care diversion capacity % (0-50)"
    )
    virtual_ward_capacity_pct: float = Field(
        0.0, ge=0.0, le=40.0, description="Virtual Ward step-down bed capacity % (0-40)"
    )


class WhatIfResponse(BaseModel):
    """What-if causal simulation outcome payload."""

    trust_code: str = Field(..., description="Target NHS Trust ODS code")
    baseline_breach_rate: float = Field(..., description="Baseline 7-day predicted breach rate %")
    did_cold_alert_effect_pp: float = Field(
        ..., description="DoWhy Difference-in-Differences treatment effect (percentage points)"
    )
    pathogen_surge_effect_pp: float = Field(
        ..., description="Estimated respiratory pathogen surge impact (percentage points)"
    )
    diversion_mitigation_pp: float = Field(
        ..., description="Estimated SDEC & Virtual Ward diversion mitigation (percentage points)"
    )
    counterfactual_breach_rate: float = Field(
        ..., description="Net counterfactual predicted breach rate %"
    )
    breach_surge_triggered: bool = Field(
        ..., description="Flag indicating breach rate >= 30% emergency threshold"
    )
    simulated_opel_tier: int = Field(..., description="Simulated OPEL escalation tier (1-4)")
    clinical_recommendations: list[str] = Field(
        ..., description="Prioritized operational interventions"
    )


class AgentQueryRequest(BaseModel):
    """Clinical-Ops Agent natural language query payload."""

    query: str = Field(..., min_length=3, max_length=1000, description="User operational query")
    trust_code: str = Field("REM", description="Default NHS Trust context (e.g. REM)")


class AgentQueryResponse(BaseModel):
    """Clinical-Ops Agent structured response payload."""

    response: str = Field(..., description="Synthesized clinical operational recommendation")
    citations: list[str] = Field(..., description="Verified NHS policy and Trust citations")
    trust_code: str = Field(..., description="Target NHS Trust ODS code")
    classified_intent: str = Field(..., description="Intent identified by Fast LLM classifier")
    pii_detected: bool = Field(..., description="Whether PII was intercepted and redacted")
    is_injection: bool = Field(..., description="Whether prompt injection attempt was detected")
    sanitized_query: str = Field(..., description="Scrubbed query passed to agent core")
    correlation_id: str = Field(..., description="Unique request tracing correlation ID")


class ErrorResponse(BaseModel):
    """Standardized error response payload."""

    error_code: str = Field(..., description="System error classification code")
    message: str = Field(..., description="Safe human-readable error description")
    correlation_id: str = Field(..., description="Request tracing ID for support audit")
    status_code: int = Field(..., description="HTTP status code")
    details: Any | None = Field(None, description="Structured validation error diagnostics")
