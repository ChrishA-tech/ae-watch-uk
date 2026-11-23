"""Streamlit Clinical-Ops Command Centre for AE-Watch UK.

Author: CHRISH PEP FELIX A
Project: AE-Watch UK
Target Benchmark Trust: Liverpool University Hospitals NHS Foundation Trust (ODS: REM)
"""

import os
from typing import Any

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Configure page settings
st.set_page_config(
    page_title="AE-Watch UK | Clinical-Ops Command Centre",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# NHS Theme Styling
st.markdown(
    """
    <style>
    .main-header {
        background: linear-gradient(135deg, #005EB8 0%, #003087 100%);
        padding: 18px 24px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 1.85rem;
        font-weight: 700;
    }
    .main-header p {
        color: #E8EDEE;
        margin: 5px 0 0 0;
        font-size: 0.95rem;
    }
    .metric-card {
        background-color: #F0F4F5;
        border-left: 5px solid #005EB8;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 12px;
    }
    .opel-badge-4 {
        background-color: #DA291C;
        color: white;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: bold;
    }
    .opel-badge-3 {
        background-color: #ED8B00;
        color: white;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: bold;
    }
    .opel-badge-2 {
        background-color: #FFB81C;
        color: #212B32;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: bold;
    }
    .opel-badge-1 {
        background-color: #007F3B;
        color: white;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: bold;
    }
    .citation-tag {
        background-color: #E8EDEE;
        border: 1px solid #768692;
        color: #212B32;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# API Gateway Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def call_api(method: str, endpoint: str, **kwargs: Any) -> dict[str, Any] | None:
    """Execute resilient HTTP call to FastAPI backend."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.request(method, url, **kwargs)
            if resp.status_code == 200:
                return resp.json()
            st.error(f"API Error ({resp.status_code}): {resp.text}")
            return None
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Could not connect to FastAPI Gateway at {url}: {exc}")
        return None


# Sidebar Navigation & Trust Context
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/f/fa/NHS-Logo.svg",
        width=120,
    )
    st.markdown("### Operational Settings")

    trust_options = {
        "REM": "REM - Liverpool University Hospitals NHS FT (Benchmark)",
        "RJR": "RJR - Countess of Chester Hospital NHS FT",
        "RBL": "RBL - Wirral University Teaching Hospital NHS FT",
        "RWW": "RWW - Warrington and Halton Teaching Hospitals NHS FT",
        "RBS": "RBS - Alder Hey Children's NHS FT",
        "REP": "REP - Liverpool Heart and Chest Hospital NHS FT",
    }

    selected_trust_code = st.selectbox(
        "Target NHS Trust Context:",
        options=list(trust_options.keys()),
        format_func=lambda x: trust_options[x],
        index=0,
    )

    st.markdown("---")
    st.markdown("### System Health")
    health_data = call_api("GET", "/health")
    if health_data and health_data.get("status") == "healthy":
        st.success("● Gateway Online (All Engines Healthy)")
        services = health_data.get("services", {})
        st.caption(f"PostgreSQL: {services.get('postgres', 'unknown')}")
        st.caption(f"Neo4j Graph: {services.get('neo4j', 'unknown')}")
        st.caption(f"MLflow Store: {services.get('mlflow', 'unknown')}")
    else:
        st.warning("● Gateway Warning / Degraded")

    st.markdown("---")
    st.markdown(
        """
        **System Author:**  
        **CHRISH PEP FELIX A**  
        *AE-Watch UK Clinical Intelligence*  
        Integrated Care Board: Cheshire & Merseyside (QE1)
        """
    )

# Main Banner Header
st.markdown(
    """
    <div class="main-header">
        <h1>🏥 AE-Watch UK: Winter Pressure & A&E Surge Command Centre</h1>
        <p>Operational Intelligence, Causal Cold Alert Simulation, and Multi-Horizon Breach Forecasting for NHS Integrated Care Boards</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Fetch Target Trust Forecast Data
forecast_data = call_api("GET", f"/api/v1/trusts/{selected_trust_code}/forecast")

if not forecast_data:
    st.info("Loading forecast baseline from local defaults...")
    forecast_data = {
        "trust_code": selected_trust_code,
        "trust_name": trust_options.get(selected_trust_code, selected_trust_code),
        "latest_observation_date": "2026-10-01",
        "latest_breach_rate_pct": 32.29,
        "monthly_attendances": 29263,
        "forecast_7d": {"p10": 29.49, "p50": 32.29, "p90": 35.69, "predicted_surge": True},
        "forecast_14d": {"p10": 29.34, "p50": 32.94, "p90": 37.24, "predicted_surge": True},
        "idw_neighbor_breach_rate": 24.64,
        "cold_snap_degree_days": 0.0,
        "shap_top_drivers": [
            {
                "feature": "breach_rolling_3m_mean",
                "importance": "+5.08%",
                "description": "High 3m baseline",
            },
            {
                "feature": "breach_rate_lag_1m",
                "importance": "+5.01%",
                "description": "Breach momentum",
            },
            {
                "feature": "total_cold_snap_degree_days",
                "importance": "+2.98%",
                "description": "Cold snap",
            },
            {
                "feature": "idw_neighbor_breach_rate",
                "importance": "+1.45%",
                "description": "Catchment spillover",
            },
        ],
        "catchment_neighbors_25km": [
            {
                "neighbor_code": "RJR",
                "neighbor_name": "Countess of Chester Hospital",
                "distance_km": 24.1,
                "neighbor_breach": 28.5,
                "neighbor_opel": 3,
            },
            {
                "neighbor_code": "RBL",
                "neighbor_name": "Wirral University Teaching Hospital",
                "distance_km": 8.7,
                "neighbor_breach": 29.1,
                "neighbor_opel": 3,
            },
            {
                "neighbor_code": "RWW",
                "neighbor_name": "Warrington and Halton Teaching Hospitals",
                "distance_km": 23.8,
                "neighbor_breach": 26.4,
                "neighbor_opel": 2,
            },
            {
                "neighbor_code": "RBS",
                "neighbor_name": "Alder Hey Children's NHS FT",
                "distance_km": 6.2,
                "neighbor_breach": 18.2,
                "neighbor_opel": 1,
            },
            {
                "neighbor_code": "REP",
                "neighbor_name": "Liverpool Heart and Chest Hospital",
                "distance_km": 6.8,
                "neighbor_breach": 12.1,
                "neighbor_opel": 1,
            },
        ],
    }

# 1. Executive Top Metrics Row
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

latest_breach = forecast_data["latest_breach_rate_pct"]
f7 = forecast_data["forecast_7d"]
f14 = forecast_data["forecast_14d"]

with kpi1:
    st.metric(
        label="Latest Actual Breach Rate",
        value=f"{latest_breach:.1f}%",
        delta=f"{(latest_breach - 22.0):+.1f}% vs NHS 78% Target",
        delta_color="inverse",
    )

with kpi2:
    st.metric(
        label="7-Day Predicted Breach (P50)",
        value=f"{f7['p50']:.1f}%",
        delta=f"P10-P90: [{f7['p10']:.1f}% - {f7['p90']:.1f}%]",
        delta_color="off",
    )

with kpi3:
    st.metric(
        label="14-Day Predicted Breach (P50)",
        value=f"{f14['p50']:.1f}%",
        delta=f"P10-P90: [{f14['p10']:.1f}% - {f14['p90']:.1f}%]",
        delta_color="off",
    )

with kpi4:
    opel_tier = (
        4 if f7["p50"] >= 35.0 else (3 if f7["p50"] >= 30.0 else (2 if f7["p50"] >= 24.0 else 1))
    )
    badge_color = (
        "#DA291C"
        if opel_tier == 4
        else ("#ED8B00" if opel_tier == 3 else ("#FFB81C" if opel_tier == 2 else "#007F3B"))
    )
    st.markdown(
        f"""
        <div style="background-color: {badge_color}; color: white; padding: 12px; border-radius: 8px; text-align: center;">
            <div style="font-size: 0.75rem; text-transform: uppercase; font-weight: 600;">Current OPEL Tier</div>
            <div style="font-size: 1.6rem; font-weight: 800;">OPEL {opel_tier}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi5:
    idw_rate = forecast_data.get("idw_neighbor_breach_rate", 24.64)
    st.metric(
        label="Catchment Spillover (25km)",
        value=f"{idw_rate:.1f}%",
        delta="IDW Neighbor Breach Pressure",
        delta_color="off",
    )

st.markdown("---")

# 2. Geospatial Map & Multi-Horizon Forecast Charts
col_map, col_chart = st.columns([1, 1])

with col_map:
    st.subheader("🗺️ Cheshire & Merseyside ICB (QE1) Catchment Network")
    st.caption(
        "Visualizing 25 km proximity spillover corridors around Liverpool University Hospitals NHS FT (REM)"
    )

    # Prepare Trust Map Data
    map_rows = [
        {
            "ods": "REM",
            "name": "Liverpool University Hospitals NHS FT",
            "lat": 53.4084,
            "lon": -2.9669,
            "breach": latest_breach,
            "opel": opel_tier,
            "is_target": True,
            "attendances": forecast_data["monthly_attendances"],
        },
        {
            "ods": "RBL",
            "name": "Wirral University Teaching Hospital",
            "lat": 53.3644,
            "lon": -3.0782,
            "breach": 29.1,
            "opel": 3,
            "is_target": False,
            "attendances": 14200,
        },
        {
            "ods": "RBS",
            "name": "Alder Hey Children's NHS FT",
            "lat": 53.4245,
            "lon": -2.8943,
            "breach": 18.2,
            "opel": 1,
            "is_target": False,
            "attendances": 8900,
        },
        {
            "ods": "REP",
            "name": "Liverpool Heart and Chest Hospital",
            "lat": 53.4089,
            "lon": -2.8901,
            "breach": 12.1,
            "opel": 1,
            "is_target": False,
            "attendances": 4100,
        },
        {
            "ods": "RWW",
            "name": "Warrington and Halton Teaching Hospitals",
            "lat": 53.3852,
            "lon": -2.5937,
            "breach": 26.4,
            "opel": 2,
            "is_target": False,
            "attendances": 11800,
        },
        {
            "ods": "RJR",
            "name": "Countess of Chester Hospital",
            "lat": 53.2128,
            "lon": -2.9004,
            "breach": 28.5,
            "opel": 3,
            "is_target": False,
            "attendances": 9700,
        },
    ]
    df_map = pd.DataFrame(map_rows)

    fig_map = px.scatter_mapbox(
        df_map,
        lat="lat",
        lon="lon",
        color="opel",
        size="breach",
        size_max=24,
        hover_name="name",
        hover_data={
            "ods": True,
            "breach": ":.1f%",
            "opel": True,
            "attendances": ":,",
            "lat": False,
            "lon": False,
        },
        color_continuous_scale=[
            [0, "#007F3B"],
            [0.33, "#FFB81C"],
            [0.66, "#ED8B00"],
            [1.0, "#DA291C"],
        ],
        range_color=[1, 4],
        zoom=9.5,
        center={"lat": 53.38, "lon": -2.90},
        mapbox_style="carto-positron",
        title="Active Trust Escalation Tiers & 25 km Proximity Network",
    )
    fig_map.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0}, height=380)
    st.plotly_chart(fig_map, use_container_width=True)

with col_chart:
    st.subheader("📈 Multi-Horizon Forecast Fan Chart & TreeSHAP Drivers")

    tab1, tab2 = st.tabs(["Multi-Horizon Fan Chart", "TreeSHAP Local Drivers"])

    with tab1:
        # Fan Chart
        horizons = ["Historical (Oct 26)", "7-Day Forecast", "14-Day Forecast"]
        p50_series = [latest_breach, f7["p50"], f14["p50"]]
        p10_series = [latest_breach, f7["p10"], f14["p10"]]
        p90_series = [latest_breach, f7["p90"], f14["p90"]]

        fig_fan = go.Figure()

        # Shaded 80% Prediction Interval
        fig_fan.add_trace(
            go.Scatter(
                x=horizons + horizons[::-1],
                y=p90_series + p10_series[::-1],
                fill="toself",
                fillcolor="rgba(0, 94, 184, 0.2)",
                line={"color": "rgba(255,255,255,0)"},
                name="80% Prediction Interval (P10 - P90)",
            )
        )

        # Median P50 Line
        fig_fan.add_trace(
            go.Scatter(
                x=horizons,
                y=p50_series,
                mode="lines+markers+text",
                line={"color": "#005EB8", "width": 3},
                marker={"size": 10, "color": "#003087"},
                text=[f"{v:.1f}%" for v in p50_series],
                textposition="top center",
                name="Median Forecast (P50)",
            )
        )

        # NHS 4-Hour Standard Target Breach Cap (22% = 78% compliance)
        fig_fan.add_hline(
            y=22.0,
            line_dash="dash",
            line_color="#007F3B",
            annotation_text="NHS 78% Standard (22% Breach Cap)",
            annotation_position="bottom right",
        )

        # Emergency Surge Threshold (30% Breach)
        fig_fan.add_hline(
            y=30.0,
            line_dash="dot",
            line_color="#DA291C",
            annotation_text="Emergency Surge Threshold (30%)",
            annotation_position="top left",
        )

        fig_fan.update_layout(
            yaxis_title="4-Hour Breach Rate (%)",
            xaxis_title="Horizon",
            height=340,
            margin={"r": 10, "t": 20, "l": 10, "b": 10},
            legend={"orientation": "h", "y": -0.2},
        )
        st.plotly_chart(fig_fan, use_container_width=True)

    with tab2:
        # TreeSHAP Waterfall Chart
        shap_items = forecast_data.get("shap_top_drivers", [])
        features = [item["feature"] for item in shap_items]
        importances = [
            float(item["importance"].replace("+", "").replace("%", "")) for item in shap_items
        ]

        fig_shap = px.bar(
            x=importances,
            y=features,
            orientation="h",
            labels={"x": "Breach Rate Impact (Percentage Points)", "y": "Feature"},
            color=importances,
            color_continuous_scale="Reds",
            title=f"TreeSHAP Attribution for {selected_trust_code}",
        )
        fig_shap.update_layout(height=340, margin={"r": 10, "t": 35, "l": 10, "b": 10})
        st.plotly_chart(fig_shap, use_container_width=True)

st.markdown("---")

# 3. Interactive Winter Surge What-If Simulator
st.subheader("❄️ Interactive Winter Surge What-If Simulator (Causal DiD)")
st.caption(
    "Adjust seasonal winter shocks and operational mitigations. Evaluated using Phase 2's verified DoWhy Difference-in-Differences point estimate (+2.058 pp)."
)

sim_col1, sim_col2, sim_col3 = st.columns([1, 1, 1])

with sim_col1:
    cold_alert = st.select_slider(
        "UKHSA Cold Health Alert Level:",
        options=["Green", "Yellow", "Amber", "Red"],
        value="Amber",
        help="Amber/Red alerts trigger a statistically verified +2.058 percentage point breach rate surge.",
    )
    norovirus_flu = st.slider(
        "Norovirus & Flu Surge (% increase):",
        min_value=0.0,
        max_value=50.0,
        value=15.0,
        step=5.0,
        help="Compounds emergency respiratory presentations (+0.12 pp breach per % surge).",
    )

with sim_col2:
    sdec_diversion = st.slider(
        "Same Day Emergency Care (SDEC) Diversion (%):",
        min_value=0.0,
        max_value=40.0,
        value=15.0,
        step=5.0,
        help="Diverts ambulatory frail elderly and low-acuity admissions (-0.15 pp breach per % diversion).",
    )
    virtual_ward = st.slider(
        "Virtual Ward Step-Down Capacity (%):",
        min_value=0.0,
        max_value=30.0,
        value=10.0,
        step=5.0,
        help="Releases inpatient acute beds for emergency admissions (-0.08 pp breach per % capacity).",
    )

with sim_col3:
    # Trigger simulation via API
    sim_payload = {
        "trust_code": selected_trust_code,
        "cold_alert_level": cold_alert,
        "norovirus_flu_surge_pct": norovirus_flu,
        "sdec_diversion_capacity_pct": sdec_diversion,
        "virtual_ward_capacity_pct": virtual_ward,
    }
    sim_result = call_api("POST", "/api/v1/simulate/what-if", json=sim_payload)

    if not sim_result:
        # Fallback local calculation
        baseline_rate = f7["p50"]
        did_effect = (
            2.058 if cold_alert in ("Amber", "Red") else (1.029 if cold_alert == "Yellow" else 0.0)
        )
        pathogen_effect = norovirus_flu * 0.12
        mitigation = sdec_diversion * 0.15 + virtual_ward * 0.08
        counterfactual = round(
            max(0.0, baseline_rate + did_effect + pathogen_effect - mitigation), 2
        )
        sim_opel = (
            4
            if counterfactual >= 35.0
            else (3 if counterfactual >= 30.0 else (2 if counterfactual >= 24.0 else 1))
        )
        sim_result = {
            "baseline_breach_rate": baseline_rate,
            "did_cold_alert_effect_pp": did_effect,
            "pathogen_surge_effect_pp": round(pathogen_effect, 2),
            "diversion_mitigation_pp": round(mitigation, 2),
            "counterfactual_breach_rate": counterfactual,
            "breach_surge_triggered": (counterfactual >= 30.0),
            "simulated_opel_tier": sim_opel,
            "clinical_recommendations": [
                f"Activate OPEL {sim_opel} Executive Escalation protocols.",
                "Enforce 45-minute fit-to-sit ambulance cohorting.",
                "Expand SDEC operational window.",
            ],
        }

    st.markdown("#### Counterfactual Outcome")
    cf_rate = sim_result["counterfactual_breach_rate"]
    base_rate = sim_result["baseline_breach_rate"]
    diff = cf_rate - base_rate

    st.metric(
        label="Counterfactual Predicted Breach",
        value=f"{cf_rate:.1f}%",
        delta=f"{diff:+.2f}% net change",
        delta_color="inverse",
    )

    sim_opel = sim_result["simulated_opel_tier"]
    st.markdown(
        f"**Simulated Escalation State:** <span class='opel-badge-{sim_opel}'>OPEL {sim_opel}</span>",
        unsafe_allow_html=True,
    )

    st.markdown("**Prioritized Action Directives:**")
    for rec in sim_result.get("clinical_recommendations", []):
        st.markdown(f"- 📋 {rec}")

st.markdown("---")

# 4. Embedded Clinical-Ops AI Copilot
st.subheader("🤖 Clinical-Ops AI Copilot (LangGraph & NHS Standards RAG)")
st.caption(
    "Interactive operational decision assistant powered by dual-LLM cognitive routing, pgvector NHS standards, and 100% PII guardrails."
)

preset_queries = [
    "Assess current 7-day winter capacity and OPEL escalation for Liverpool REM",
    "What is the operational protocol if ambulance handovers exceed 45 minutes?",
    "Simulate counterfactual surge if UKHSA raises Cold Alert to Amber",
    "What are the diversion criteria for Same Day Emergency Care (SDEC)?",
]

col_q, col_quick = st.columns([3, 1])

with col_quick:
    st.markdown("**Quick Inquiries:**")
    for q_text in preset_queries:
        if st.button(q_text, key=f"btn_{q_text[:20]}"):
            st.session_state["copilot_input"] = q_text

with col_q:
    user_query = st.text_input(
        "Enter clinical operational inquiry:",
        value=st.session_state.get(
            "copilot_input",
            "Assess current 7-day winter capacity and OPEL escalation for Liverpool REM",
        ),
        key="input_copilot",
    )
    run_copilot = st.button("🚀 Consult Clinical Copilot", type="primary")

if run_copilot and user_query:
    with st.spinner(
        "Analyzing operational state, querying knowledge graph, and verifying NHS standards..."
    ):
        agent_resp = call_api(
            "POST",
            "/api/v1/agent/query",
            json={"query": user_query, "trust_code": selected_trust_code},
        )

        if agent_resp:
            # Display Safety & Guardrail Indicators
            g1, g2, g3, g4 = st.columns(4)
            with g1:
                st.markdown(f"**Intent:** `{agent_resp.get('classified_intent')}`")
            with g2:
                pii_flag = "⚠️ Redacted" if agent_resp.get("pii_detected") else "✅ None"
                st.markdown(f"**PII Status:** {pii_flag}")
            with g3:
                inj_flag = "🚨 Blocked" if agent_resp.get("is_injection") else "✅ Secure"
                st.markdown(f"**Prompt Safety:** {inj_flag}")
            with g4:
                st.markdown(f"**Trace ID:** `{agent_resp.get('correlation_id', 'local')[:8]}...`")

            # Synthesized Response
            st.markdown("#### Clinical Synthesis & Directives")
            st.markdown(agent_resp.get("response", ""))

            # Citations
            citations = agent_resp.get("citations", [])
            if citations:
                st.markdown("---")
                st.markdown("**Verified Policy & Source Citations:**")
                citation_html = "".join(
                    [f"<span class='citation-tag'>📄 {c}</span>" for c in citations]
                )
                st.markdown(citation_html, unsafe_allow_html=True)
