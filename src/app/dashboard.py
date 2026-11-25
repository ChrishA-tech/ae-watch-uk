"""Streamlit v2 Clinical-Ops & Conformal Command Centre Dashboard.

Integrates seamlessly with FastAPI (src/app/main.py), DuckDB telemetry, MAPIE 90% conformal
intervals, sliced error audits, and the LangGraph OPEL Copilot with degraded-feed fallback.

Author: CHRISH PEP FELIX A
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import duckdb
import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import structlog

logger = structlog.get_logger("ae_watch.v2.dashboard")

from src.agents.clinical_copilot import calculate_opel_tier, clinical_copilot
from src.ingestion.ae_pipeline import DEFAULT_DUCKDB_PATH, apply_uk_gdpr_pseudonymisation
from src.ingestion.live_nhs_connectors import (
    NHS_ACUTE_TRUST_HUBS,
    fetch_live_nhs_and_weather_telemetry,
)
from src.models.conformal_forecaster import DEFAULT_MODEL_BUNDLE_PATH, predict_trust_conformal

st.set_page_config(
    page_title="AE-Watch UK v2 | Clinical Escalation Command Centre",
    page_icon="🏥",
    layout="wide",
)

API_URL = os.getenv("AEWATCH_API_URL", "http://127.0.0.1:8000")


def load_telemetry_panel() -> tuple[pd.DataFrame, str]:
    """Load telemetry from DuckDB with graceful LIVE_NHS_FEED_DEGRADED fallback."""
    if DEFAULT_DUCKDB_PATH.exists():
        try:
            with duckdb.connect(str(DEFAULT_DUCKDB_PATH), read_only=True) as conn:
                df = conn.execute("SELECT * FROM trust_sitrep_daily ORDER BY observation_date").df()
            if not df.empty:
                status_flag = str(df["feed_status"].iloc[-1])
                return df, status_flag
        except Exception as exc:  # noqa: BLE001
            logger.warning("dashboard_duckdb_read_fallback", error=str(exc))

    fallback_df = apply_uk_gdpr_pseudonymisation(fetch_live_nhs_and_weather_telemetry(live=False))
    return fallback_df, "LIVE_NHS_FEED_DEGRADED"


def fetch_api_telemetry(ods_code: str, panel_df: pd.DataFrame) -> dict[str, Any]:
    """Query FastAPI endpoint if reachable, else execute local degraded fallback cleanly."""
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{API_URL}/api/v1/trusts/{ods_code}/telemetry")
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("dashboard_api_fallback_local", error=str(exc), trust=ods_code)

    sub = panel_df[panel_df["trust_ods_code"] == ods_code].tail(1)
    rec = sub.iloc[0].to_dict()
    opel = calculate_opel_tier(
        float(rec["four_hour_compliance_ratio"]),
        float(rec["bed_occupancy_ratio"]),
        int(rec["twelve_hour_trolley_waits"]),
        int(rec["cold_snap_trigger"]),
    )
    if DEFAULT_MODEL_BUNDLE_PATH.exists():
        conformal = predict_trust_conformal(sub)
    else:
        b = round(float(rec["four_hour_breach_rate_pct"]), 2)
        t = float(rec["twelve_hour_trolley_waits"])
        conformal = {
            "breach_rate_pct": {
                "point": b,
                "pi90_lower": max(0.0, b - 4.5),
                "pi90_upper": min(100.0, b + 4.5),
            },
            "twelve_hour_trolley_waits": {
                "point": t,
                "pi90_lower": max(0.0, t - 10.0),
                "pi90_upper": t + 10.0,
            },
            "shap_top_drivers": [],
        }
    return {
        "trust_ods_code": ods_code,
        "trust_name": rec["trust_name"],
        "region": rec["region"],
        "trust_type": rec["trust_type"],
        "observation_date": str(rec["observation_date"]),
        "feed_status": str(rec.get("feed_status", "LIVE_NHS_FEED_DEGRADED")),
        "opel_assessment": opel,
        "conformal_forecast_90ci": conformal,
        "weather_and_pathogens": {
            "temp_c": float(rec["temp_c"]),
            "min_temp_c": float(rec["min_temp_c"]),
            "cold_snap_trigger": int(rec["cold_snap_trigger"]),
            "ukhsa_flu_admission_rate": float(rec["ukhsa_flu_admission_rate"]),
            "ukhsa_rsv_admission_rate": float(rec["ukhsa_rsv_admission_rate"]),
        },
    }


def main() -> None:
    """Render Streamlit v2 Clinical-Ops Command Centre."""
    panel_df, feed_status = load_telemetry_panel()

    st.title("🏥 AE-Watch UK v2: NHS A&E Surge & Conformal Escalation Command Centre")
    st.caption(
        f"**Lead Architect:** CHRISH PEP FELIX A | **Telemetry Status:** `{feed_status}` | "
        "**Validation:** Trust-Grouped LightGBM + MAPIE 90% Conformal Intervals"
    )

    if feed_status == "LIVE_NHS_FEED_DEGRADED":
        st.warning("Operating in `LIVE_NHS_FEED_DEGRADED` offline baseline fallback mode.")

    trust_map = {
        h["trust_ods_code"]: f"{h['trust_ods_code']} — {h['trust_name']}"
        for h in NHS_ACUTE_TRUST_HUBS
    }
    selected_ods = st.sidebar.selectbox(
        "Select NHS Acute Trust Hub",
        options=list(trust_map.keys()),
        format_func=lambda k: trust_map[k],
    )

    data = fetch_api_telemetry(selected_ods, panel_df)
    opel = data["opel_assessment"]
    cf = data["conformal_forecast_90ci"]
    wx = data["weather_and_pathogens"]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("OPEL Escalation Tier", opel["opel_tier"], opel["severity"])
    c2.metric(
        "4h Breach Forecast (90% CI)",
        f"{cf['breach_rate_pct']['point']:.1f}%",
        f"[{cf['breach_rate_pct']['pi90_lower']:.1f}% – {cf['breach_rate_pct']['pi90_upper']:.1f}%]",
    )
    c3.metric(
        "12h Trolley Waits (90% CI)",
        f"{cf['twelve_hour_trolley_waits']['point']:.0f}",
        f"[{cf['twelve_hour_trolley_waits']['pi90_lower']:.0f} – {cf['twelve_hour_trolley_waits']['pi90_upper']:.0f}]",
    )
    c4.metric("Acute Bed Occupancy", f"{opel['bed_occupancy_pct']:.1f}%", "92% Severe Threshold")
    c5.metric(
        "Cold-Snap / Flu Exposure",
        f"{wx['temp_c']:.1f}°C",
        f"Flu: {wx['ukhsa_flu_admission_rate']:.1f}/100k",
    )

    st.markdown("---")
    col_left, col_right = st.columns(2)

    trust_hist = panel_df[panel_df["trust_ods_code"] == selected_ods].sort_values(
        "observation_date"
    )
    with col_left:
        st.subheader(f"📈 28-Day 4-Hour Breach Trajectory — {selected_ods}")
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=trust_hist["observation_date"],
                y=trust_hist["four_hour_breach_rate_pct"],
                mode="lines+markers",
                name="Observed Breach Rate (%)",
                line={"color": "#005EB8", "width": 3},
            )
        )
        fig.add_hline(
            y=22.0, line_dash="dash", line_color="#007F3B", annotation_text="NHS 78% Standard"
        )
        fig.update_layout(height=340, margin={"t": 20, "b": 20, "l": 10, "r": 10})
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("🧠 Top Global SHAP Surge Drivers")
        drivers = cf.get("shap_top_drivers", [])
        if drivers:
            df_shap = pd.DataFrame(drivers)
            fig_shap = px.bar(
                df_shap,
                x="mean_abs_shap",
                y="feature",
                orientation="h",
                color="mean_abs_shap",
                color_continuous_scale="Blues",
            )
            fig_shap.update_layout(height=340, margin={"t": 20, "b": 20, "l": 10, "r": 10})
            st.plotly_chart(fig_shap, use_container_width=True)
        else:
            st.info("Run `python -m src.run_pipeline --live` to materialize MAPIE + SHAP bundle.")

    st.markdown("---")
    st.subheader("🤖 Guarded Clinical Escalation & OPEL Copilot (NHS OPEL / NICE NG94 / RCEM)")
    query = st.text_input(
        "Operational question:",
        value=f"What OPEL escalation and 45-minute ambulance handover actions apply for Trust {selected_ods}?",
    )
    if st.button("Ask OPEL Copilot", type="primary"):
        res = clinical_copilot.ask(query=query, trust_ods_code=selected_ods)
        st.markdown(res["final_response"])
        st.caption(
            f"PII Redacted: `{res['pii_detected']}` | Prompt Injection Blocked: `{res['is_injection']}` | "
            f"Citations Verified: `{res['citation_verified']}` | Sources: `{', '.join(res['citations'])}`"
        )

    report_path = Path("docs/ERROR_ANALYSIS_REPORT.md")
    if report_path.exists():
        with st.expander("📊 View Sliced Conformal Error Analysis Report"):
            st.markdown(report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
