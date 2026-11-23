"""Pytest suite for AE-Watch UK FastAPI Clinical-Ops Gateway.

Author: CHRISH PEP FELIX A
Project: AE-Watch UK
"""

from fastapi.testclient import TestClient

from ae_watch.api.app import app

client = TestClient(app)


def test_api_health_endpoint():
    """Verify health and readiness probe reporting on PostgreSQL, Neo4j, and MLflow."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["author"] == "CHRISH PEP FELIX A"
    assert data["services"]["postgres"] == "healthy"
    assert data["services"]["neo4j"] == "healthy"
    assert data["services"]["mlflow"] == "ready"


def test_api_forecast_endpoint_rem_benchmark():
    """Verify Liverpool REM forecast returns valid quantiles, SHAP drivers, and catchment peers."""
    response = client.get("/api/v1/trusts/REM/forecast")
    assert response.status_code == 200
    data = response.json()
    assert data["trust_code"] == "REM"
    assert "Liverpool" in data["trust_name"]

    # Monotonicity test: P10 <= P50 <= P90
    f7 = data["forecast_7d"]
    assert f7["p10"] <= f7["p50"] <= f7["p90"]
    assert f7["horizon_days"] == 7

    f14 = data["forecast_14d"]
    assert f14["p10"] <= f14["p50"] <= f14["p90"]
    assert f14["horizon_days"] == 14

    # TreeSHAP drivers
    assert len(data["shap_top_drivers"]) >= 3
    assert any("breach" in d["feature"] for d in data["shap_top_drivers"])

    # Catchment neighbors within 25 km
    assert len(data["catchment_neighbors_25km"]) > 0
    for neighbor in data["catchment_neighbors_25km"]:
        assert neighbor["distance_km"] <= 25.0


def test_api_what_if_simulation_endpoint():
    """Verify what-if causal simulator injects DoWhy DiD effect and mitigations correctly."""
    payload = {
        "trust_code": "REM",
        "cold_alert_level": "Amber",
        "norovirus_flu_surge_pct": 20.0,
        "sdec_diversion_capacity_pct": 10.0,
        "virtual_ward_capacity_pct": 5.0,
    }
    response = client.post("/api/v1/simulate/what-if", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["trust_code"] == "REM"
    assert data["did_cold_alert_effect_pp"] == 2.058  # Exact Phase 2 DiD effect
    assert data["pathogen_surge_effect_pp"] == round(20.0 * 0.12, 3)
    assert data["diversion_mitigation_pp"] == round(10.0 * 0.15 + 5.0 * 0.08, 3)
    assert data["simulated_opel_tier"] in (1, 2, 3, 4)
    assert len(data["clinical_recommendations"]) > 0


def test_api_correlation_id_and_header_propagation():
    """Verify that custom X-Correlation-ID headers are honored and propagated."""
    custom_id = "test-corr-uuid-12345"
    response = client.get("/health", headers={"X-Correlation-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == custom_id


def test_api_validation_error_structure_no_leakage():
    """Verify that invalid schema payloads return HTTP 422 with correlation ID and no stack trace."""
    # norovirus_flu_surge_pct > 100 violates Pydantic le=100.0 constraint
    payload = {
        "trust_code": "REM",
        "norovirus_flu_surge_pct": 250.0,
    }
    response = client.post("/api/v1/simulate/what-if", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "VALIDATION_ERROR"
    assert "correlation_id" in data
    assert data["status_code"] == 422
    assert "Traceback" not in response.text
