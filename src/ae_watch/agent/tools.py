"""Typed Clinical and Operational Tools for AE-Watch Agent.

Author: CHRISH PEP FELIX A
Project: AE-Watch UK
"""

from typing import Any

import psycopg

from ae_watch.config import settings
from ae_watch.rag.hybrid_retriever import hybrid_retriever
from ae_watch.utils.logger import logger


def inspect_forecast_and_shap(trust_code: str = "REM") -> dict[str, Any]:
    """Inspect latest historical and multi-horizon forecasted breach rates and SHAP drivers for a Trust."""
    logger.info("tool_inspect_forecast_and_shap", trust_code=trust_code)

    query_sql = """
    SELECT
        trust_code,
        period_date,
        breach_4hr_pct,
        target_breach_rate_horizon_7d,
        target_breach_rate_horizon_14d,
        target_surge_binary_7d,
        total_attendances,
        total_cold_snap_degree_days,
        idw_neighbor_breach_rate,
        flu_admission_rate,
        covid_positivity_pct,
        h3_res7_cell
    FROM gold.ml_trust_forecast_features
    WHERE trust_code = %s
    ORDER BY period_date DESC
    LIMIT 1;
    """

    with psycopg.connect(settings.postgres_connection_uri) as conn, conn.cursor() as cur:
        cur.execute(query_sql, (trust_code.upper(),))
        cols = [desc[0] for desc in cur.description]
        row = cur.fetchone()

    if not row:
        return {
            "trust_code": trust_code,
            "status": "not_found",
            "message": f"No features found for Trust {trust_code}",
        }

    rec = dict(zip(cols, row))

    # Top global and local SHAP feature drivers from Phase 2 model
    top_drivers = [
        {
            "feature": "breach_rolling_3m_mean",
            "importance": "+5.08%",
            "description": "High 3-month baseline pressure",
        },
        {
            "feature": "breach_rate_lag_1m",
            "importance": "+5.01%",
            "description": "Persistent breach momentum",
        },
        {
            "feature": "idw_neighbor_breach_rate",
            "importance": "+1.45%",
            "description": "Catchment spillover from Wirral/Chester",
        },
        {
            "feature": "total_cold_snap_degree_days",
            "importance": "+2.98%",
            "description": "Sub-zero cold snap shock",
        },
    ]

    return {
        "trust_code": rec["trust_code"],
        "latest_observation_date": str(rec["period_date"]),
        "latest_breach_rate_pct": float(rec["breach_4hr_pct"] or 0.0),
        "forecast_7d_breach_rate_pct": float(rec["target_breach_rate_horizon_7d"] or 0.0),
        "forecast_14d_breach_rate_pct": float(rec["target_breach_rate_horizon_14d"] or 0.0),
        "surge_alert_binary_7d": int(rec["target_surge_binary_7d"] or 0),
        "monthly_attendances": int(rec["total_attendances"] or 0),
        "neighbor_idw_breach_pct": float(rec["idw_neighbor_breach_rate"] or 0.0),
        "cold_snap_degree_days": float(rec["total_cold_snap_degree_days"] or 0.0),
        "h3_cell_res7": str(rec["h3_res7_cell"]),
        "shap_top_drivers": top_drivers,
    }


def simulate_causal_cold_alert(
    trust_code: str = "REM", alert_level: str = "Amber"
) -> dict[str, Any]:
    """Simulate the causal impact of UKHSA Cold Health Alerts on A&E breach rates using Phase 2 DiD."""
    logger.info("tool_simulate_causal_cold_alert", trust_code=trust_code, alert_level=alert_level)

    # Base observation
    latest = inspect_forecast_and_shap(trust_code)
    base_breach = latest.get("forecast_7d_breach_rate_pct", 32.0)

    # Phase 2 DoWhy Difference-in-Differences point estimate: +2.058 percentage points
    causal_delta = (
        2.058
        if alert_level.capitalize() in ("Amber", "Red")
        else (1.029 if alert_level.capitalize() == "Yellow" else 0.0)
    )
    simulated_breach = round(base_breach + causal_delta, 2)
    breach_surge_triggered = simulated_breach >= 30.0

    return {
        "trust_code": trust_code.upper(),
        "simulated_alert_level": alert_level.capitalize(),
        "baseline_predicted_breach_rate": base_breach,
        "did_causal_increase_percentage_points": causal_delta,
        "simulated_post_alert_breach_rate": simulated_breach,
        "breach_surge_triggered": breach_surge_triggered,
        "p_value": 0.00003,
        "ci_95": (1.094, 3.023),
        "recommendation": (
            "Activate OPEL 3/4 bed escalation, open respiratory Virtual Ward step-down beds, "
            "and establish fit-to-sit 45-minute ambulance handover cohorting."
            if breach_surge_triggered
            else "Maintain OPEL 2 monitoring with standard SDEC ambulant diversion."
        ),
    }


def retrieve_hybrid_clinical_policy(query: str, trust_code: str = "REM") -> dict[str, Any]:
    """Search pgvector standards and Neo4j graph context for clinical operational policies."""
    logger.info("tool_retrieve_hybrid_clinical_policy", query=query, trust_code=trust_code)
    return hybrid_retriever.retrieve(query=query, trust_code=trust_code, top_k=3)
