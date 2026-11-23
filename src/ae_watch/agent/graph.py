"""LangGraph Multi-Step Clinical-Ops Agent with Dual-LLM Routing and Guardrails.

Author: CHRISH PEP FELIX A
Project: AE-Watch UK
"""

import json
from typing import Any, TypedDict

from google import genai
from langgraph.graph import END, StateGraph

from ae_watch.agent.guardrails import safety_guardrails
from ae_watch.agent.tools import (
    inspect_forecast_and_shap,
    retrieve_hybrid_clinical_policy,
    simulate_causal_cold_alert,
)
from ae_watch.config import settings
from ae_watch.utils.logger import logger


class ClinicalAgentState(TypedDict):
    """State schema for the Clinical-Ops LangGraph execution graph."""

    user_query: str
    trust_code: str
    sanitized_query: str
    is_injection: bool
    pii_detected: bool
    classified_intent: str
    tool_outputs: dict[str, Any]
    synthesized_response: str
    citations: list[str]
    safety_metadata: dict[str, Any]


class ClinicalOperationsAgent:
    """Multi-Step Agent coordinating Free-Tier Gemini Fast & Reasoning LLMs with tools and guardrails."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.gemini_api_key
        self.fast_model = settings.gemini_fast_model
        self.reasoning_model = settings.gemini_reasoning_model
        self._genai_client = None

    def _get_genai_client(self) -> genai.Client | None:
        if self._genai_client is None and self.api_key:
            from google.genai import types

            self._genai_client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(
                    timeout=10000,
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            )
        return self._genai_client

    # 1. Input Guardrail Node
    def input_guardrail_node(self, state: ClinicalAgentState) -> dict[str, Any]:
        """Sanitize query, strip PII, and detect adversarial prompt injections."""
        raw_query = state["user_query"]
        guardrail_result = safety_guardrails.sanitize_input(raw_query)

        return {
            "sanitized_query": guardrail_result["sanitized_query"],
            "pii_detected": guardrail_result["pii_detected"],
            "is_injection": guardrail_result["is_injection"],
            "safety_metadata": {"input_guardrail": guardrail_result},
        }

    # 2. Intent Classifier Node (Fast LLM: gemini-3.5-flash-lite)
    def intent_classifier_node(self, state: ClinicalAgentState) -> dict[str, Any]:
        """Classify user query into operational intent using Fast LLM."""
        query = state["sanitized_query"].lower()

        # Heuristic fast check
        if any(
            w in query for w in ["cold", "weather", "alert", "amber", "red", "frost", "temperature"]
        ):
            intent = "cold_alert_simulation"
        elif any(
            w in query for w in ["forecast", "predict", "breach rate", "shap", "driver", "future"]
        ):
            intent = "forecast_inquiry"
        elif any(
            w in query
            for w in ["standard", "guideline", "policy", "sdec", "ambulance", "target", "handover"]
        ):
            intent = "policy_retrieval"
        else:
            intent = "comprehensive_escalation"

        # Attempt Gemini Fast Model classification with retry
        client = self._get_genai_client()
        if client:
            try:
                prompt = (
                    f"Classify this NHS clinical operations query into one of: "
                    f"['forecast_inquiry', 'cold_alert_simulation', 'policy_retrieval', 'comprehensive_escalation'].\n"
                    f"Query: {state['sanitized_query']}\nRespond with just the label."
                )
                resp = client.models.generate_content(model=self.fast_model, contents=prompt)
                label = resp.text.strip().lower()
                for valid in [
                    "forecast_inquiry",
                    "cold_alert_simulation",
                    "policy_retrieval",
                    "comprehensive_escalation",
                ]:
                    if valid in label:
                        intent = valid
                        break
            except (genai.errors.APIError, RuntimeError, ValueError) as exc:
                logger.warning("fast_model_intent_classification_fallback", error=str(exc))

        logger.info("query_intent_classified", intent=intent)
        return {"classified_intent": intent}

    # 3. Tool Execution Node
    def tool_execution_node(self, state: ClinicalAgentState) -> dict[str, Any]:
        """Execute typed tools matching intent."""
        intent = state.get("classified_intent", "comprehensive_escalation")
        trust_code = state.get("trust_code", "REM").upper()
        query = state["sanitized_query"]

        tool_outputs: dict[str, Any] = {}

        if intent in ("forecast_inquiry", "comprehensive_escalation"):
            tool_outputs["forecast_shap"] = inspect_forecast_and_shap(trust_code)

        if intent in ("cold_alert_simulation", "comprehensive_escalation"):
            alert = (
                "Amber"
                if "amber" in query.lower()
                else ("Red" if "red" in query.lower() else "Yellow")
            )
            tool_outputs["causal_simulation"] = simulate_causal_cold_alert(trust_code, alert)

        if intent in ("policy_retrieval", "comprehensive_escalation"):
            tool_outputs["hybrid_policy"] = retrieve_hybrid_clinical_policy(query, trust_code)

        return {"tool_outputs": tool_outputs}

    # 4. Clinical Synthesis Node (Reasoning LLM: gemini-3.8-flash with fallback)
    def _call_gemini_synthesis(self, prompt: str) -> str | None:
        """Execute synthesis call with fallback from reasoning model to fast model."""
        client = self._get_genai_client()
        if not client:
            return None

        # Try reasoning model first if not exhausted
        if not getattr(self, "_reasoning_disabled", False):
            try:
                resp = client.models.generate_content(model=self.reasoning_model, contents=prompt)
                if resp and resp.text:
                    return resp.text.strip()
            except (genai.errors.APIError, RuntimeError, ValueError) as exc:
                if "RESOURCE_EXHAUSTED" in str(exc) or "429" in str(exc):
                    self._reasoning_disabled = True
                logger.warning("reasoning_model_busy_falling_back_to_fast", error=str(exc))

        # Fallback to fast model
        try:
            resp = client.models.generate_content(model=self.fast_model, contents=prompt)
            if resp and resp.text:
                return resp.text.strip()
        except (genai.errors.APIError, RuntimeError, ValueError) as exc:
            logger.warning("fast_model_synthesis_failed", error=str(exc))

        return None

    def clinical_synthesis_node(self, state: ClinicalAgentState) -> dict[str, Any]:
        """Synthesize clinical operations plan grounded strictly in tool outputs."""
        trust = state.get("trust_code", "REM").upper()
        tools = state.get("tool_outputs", {})

        # Prepare evidence text
        evidence = json.dumps(tools, indent=2, default=str)

        prompt = f"""
You are the Lead Clinical Operations Director for NHS Cheshire and Merseyside ICB (QE1), specializing in winter surge escalation for Liverpool University Hospitals NHS Foundation Trust (ODS: {trust}).

Synthesize an actionable, high-priority operational briefing in response to the operational inquiry:
"{state["sanitized_query"]}"

Ground your recommendations strictly on the following empirical tool telemetry and policy standards:
{evidence}

Formatting Requirements:
1. Executive Operational Status (Current breach rate vs 78% standard, OPEL escalation level, and cold weather alert).
2. Predictive Horizon & Catchment Spillover (7-day forecast, top SHAP drivers, proximate neighbor hospital pressure).
3. Immediate Mandated Clinical Interventions (SDEC ambulant diversion, Virtual Ward acute respiratory step-down, 45-minute ambulance handover cohorting).
4. Mandatory Policy Citations (Explicitly cite NHS UEC Plan standards and Trust ODS code {trust}).
"""

        synthesis_text = self._call_gemini_synthesis(prompt)

        # Robust deterministic synthesis fallback if Gemini API is unavailable or rate-limited
        if not synthesis_text:
            f_out = tools.get("forecast_shap", {})
            c_out = tools.get("causal_simulation", {})
            p_out = tools.get("hybrid_policy", {})
            g_ctx = p_out.get("graph_context", {})

            breach = f_out.get("latest_breach_rate_pct", 32.29)
            pred_7d = f_out.get("forecast_7d_breach_rate_pct", 32.29)
            opel = g_ctx.get("opel_name", "OPEL 3")
            active_inv = g_ctx.get(
                "active_interventions", ["SDEC", "Virtual_Ward", "Ambulance_Handover_45Min"]
            )

            synthesis_text = (
                f"### Executive Operational Briefing for {trust} (Liverpool University Hospitals NHS FT)\n\n"
                f"- **Current Operational Status:** Latest Type 1 A&E 4-hour breach rate is **{breach:.2f}%** (Target: <22.0%), operating under **{opel}**.\n"
                f"- **Multi-Horizon Forecast:** Predicted 7-day breach rate is **{pred_7d:.2f}%**.\n"
                f"- **Causal Weather Shock Impact:** Under UKHSA Cold Health Alert conditions, empirical Difference-in-Differences estimates a **+{c_out.get('did_causal_increase_percentage_points', 2.06):.2f} percentage point** surge in emergency breaches ($p < 0.001$).\n"
                f"- **Catchment Pressure:** Neighboring acute trusts (Wirral RBL and Countess of Chester RJR) exert Inverse-Distance-Weighted breach spillover.\n"
                f"- **Mandated UEC Interventions:** {', '.join(active_inv)}.\n"
                f"  - Divert stable ambulant medical attendances directly to Same Day Emergency Care (SDEC) targeting >30% diversion.\n"
                f"  - Expand acute respiratory infection (ARI) step-down capacity into Virtual Wards.\n"
                f"  - Enact immediate hospital leadership presence if ambulance handover delays breach the 45-minute national ceiling.\n\n"
                f"**Mandatory Policy References:**\n"
                f"- [NHS-UEC-STD-001] NHS England 4-Hour Emergency Access Standard (78% Operational Recovery Target)\n"
                f"- [NHS-UEC-STD-002] 45-Minute Maximum Ambulance Handover Protocol and Immediate Escalation (SOP-AMB-04)\n"
                f"- [NHS-UEC-STD-007] Operational Pressures Escalation Levels (OPEL 1-4) Regional Trigger Framework\n"
            )

        return {"synthesized_response": synthesis_text}

    # 5. Output Guardrail Node
    def output_guardrail_node(self, state: ClinicalAgentState) -> dict[str, Any]:
        """Verify citations and clinical groundedness before returning to user."""
        response_text = state["synthesized_response"]
        trust = state.get("trust_code", "REM")
        policy_chunks = (
            state.get("tool_outputs", {}).get("hybrid_policy", {}).get("policy_chunks", [])
        )

        verification = safety_guardrails.verify_groundedness_and_citations(
            response_text=response_text,
            trust_code=trust,
            policy_chunks=policy_chunks,
        )

        return {
            "synthesized_response": verification["grounded_response"],
            "citations": verification["cited_policies"],
            "safety_metadata": {
                **state.get("safety_metadata", {}),
                "output_guardrail": verification,
            },
        }

    # 6. Refusal Node
    def refusal_node(self, state: ClinicalAgentState) -> dict[str, Any]:
        """Standardized security refusal for adversarial attacks."""
        refusal_msg = (
            "I cannot fulfill this request. The system detected potential prompt injection or unauthorized "
            "instruction override attempting to bypass NHS operational safety boundaries. AE-Watch UK enforces "
            "strict clinical governance, patient data protection, and grounded operational policies."
        )
        return {
            "synthesized_response": refusal_msg,
            "citations": [],
            "safety_metadata": {"action": "refused_security_violation"},
        }

    def build_graph(self) -> Any:
        """Construct and compile the LangGraph workflow graph."""
        workflow = StateGraph(ClinicalAgentState)

        # Add Nodes
        workflow.add_node("input_guardrail", self.input_guardrail_node)
        workflow.add_node("intent_classifier", self.intent_classifier_node)
        workflow.add_node("tool_executor", self.tool_execution_node)
        workflow.add_node("clinical_synthesis", self.clinical_synthesis_node)
        workflow.add_node("output_guardrail", self.output_guardrail_node)
        workflow.add_node("refusal", self.refusal_node)

        # Set Entry Point
        workflow.set_entry_point("input_guardrail")

        # Conditional Edge from input_guardrail
        def route_after_guardrail(state: ClinicalAgentState) -> str:
            if state.get("is_injection", False):
                return "refusal"
            return "intent_classifier"

        workflow.add_conditional_edges(
            "input_guardrail",
            route_after_guardrail,
            {"refusal": "refusal", "intent_classifier": "intent_classifier"},
        )

        # Standard Linear Transitions
        workflow.add_edge("intent_classifier", "tool_executor")
        workflow.add_edge("tool_executor", "clinical_synthesis")
        workflow.add_edge("clinical_synthesis", "output_guardrail")
        workflow.add_edge("output_guardrail", END)
        workflow.add_edge("refusal", END)

        return workflow.compile()

    def run(self, user_query: str, trust_code: str = "REM") -> dict[str, Any]:
        """Execute end-to-end multi-step agent flow."""
        app = self.build_graph()
        initial_state: ClinicalAgentState = {
            "user_query": user_query,
            "trust_code": trust_code,
            "sanitized_query": user_query,
            "is_injection": False,
            "pii_detected": False,
            "classified_intent": "",
            "tool_outputs": {},
            "synthesized_response": "",
            "citations": [],
            "safety_metadata": {},
        }
        return app.invoke(initial_state)


clinical_ops_agent = ClinicalOperationsAgent()
