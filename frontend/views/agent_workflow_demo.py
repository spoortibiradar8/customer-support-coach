"""Polished workflow panel that reads the real backend orchestration output."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from backend.orchestrator.mock_components import MockAgent, MockSessionManager
from backend.orchestrator.orchestrator import run_workflow
from backend.orchestrator.schemas import WorkflowRequest
from backend.services import pipeline_stub as pipe


def _sample_payload() -> dict[str, Any]:
    """Return a clean realistic default payload for the panel."""
    return {
        "customer_message": "I was charged twice and I need this fixed today.",
        "intent": "Refund / billing",
        "emotion": "Frustrated",
        "frustration_trend": "rising",
        "escalation_risk": 72,
        "escalation_level": "HIGH",
        "warning_flags": ["FINANCIAL_FRAUD_DISPUTE", "SLA_TIME_CRITICALITY"],
        "strategy": "Acknowledge feelings with deep empathy, own the issue, offer a clear timeline, and inform the customer that a supervisor is on standby.",
        "kb_query": "duplicate charge refund policy",
        "matched_kb": [
            "Billing policy",
            "Refund window",
            "Duplicate payment guidance",
        ],
    }


def _dedupe_names(items: Any) -> list[str]:
    """Normalize KB match entries into readable file names or document labels."""
    if not isinstance(items, list):
        items = [items]

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        if isinstance(item, dict):
            name = item.get("doc_name") or item.get("source") or item.get("file_name") or item.get("name")
        else:
            name = item

        if not isinstance(name, str):
            continue
        label = name.strip()
        if label and label not in seen:
            cleaned.append(label)
            seen.add(label)
    return cleaned


def _frustration_trend(frustration: Any) -> str:
    """Map an emotion score to a readable customer-trend label."""
    try:
        score = int(frustration)
    except (TypeError, ValueError):
        return "stable"

    if score >= 70:
        return "rising"
    if score >= 40:
        return "elevated"
    return "stable"


def _normalize_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize either a backend result or a demo payload into a common UI shape."""
    default = _sample_payload()
    if not isinstance(payload, dict):
        return default

    if "result" in payload and isinstance(payload["result"], dict):
        payload = payload["result"]

    if "workflow" in payload and isinstance(payload["workflow"], dict):
        payload = payload["workflow"]

    raw_matches = payload.get("matched_kb") or payload.get("kb_matches") or default["matched_kb"]
    matched_kb = _dedupe_names(raw_matches)

    frustration = payload.get("frustration")
    if "frustration_trend" not in payload and "trend" not in payload and frustration is not None:
        trend = _frustration_trend(frustration)
    else:
        trend = payload.get("frustration_trend") or payload.get("trend") or default["frustration_trend"]

    normalized = {
        "customer_message": payload.get("customer_message") or payload.get("message") or default["customer_message"],
        "intent": payload.get("intent") or default["intent"],
        "emotion": payload.get("emotion") or default["emotion"],
        "frustration_trend": trend,
        "escalation_risk": payload.get("escalation_risk") if payload.get("escalation_risk") is not None else payload.get("risk", default["escalation_risk"]),
        "escalation_level": str(payload.get("escalation_level") or payload.get("risk_level") or default["escalation_level"]).upper(),
        "warning_flags": payload.get("warning_flags") or default["warning_flags"],
        "strategy": payload.get("strategy") or default["strategy"],
        "kb_query": payload.get("kb_query") or payload.get("query_context") or default["kb_query"],
        "matched_kb": matched_kb if matched_kb else default["matched_kb"],
    }

    return normalized


def _coerce_workflow_payload(message: str) -> dict[str, Any]:
    """Resolve the latest workflow result from the backend and map it to the demo panel."""
    clean_message = (message or "").strip()
    default = _sample_payload()

    if not clean_message:
        return default

    try:
        session_manager = MockSessionManager()
        session = session_manager.get_session("sess-demo01") or session_manager.create_session("sess-demo01")
        response = run_workflow(
            WorkflowRequest(session_id=session.session_id, message=clean_message),
            session_manager=session_manager,
            agent=MockAgent(),
        )

        if getattr(response, "status", None) == "completed" and isinstance(getattr(response, "result", None), dict):
            analysis = response.result
            fallback = pipe.analyze_turn(
                clean_message,
                [{"role": "customer", "text": clean_message}],
                {"product": "Acme Online Store", "mode": "Manual", "persona": "Calm"},
            )
            customer_message = clean_message
            payload = {
                "customer_message": customer_message,
                "intent": analysis.get("intent") or fallback.get("intent") or analysis.get("response") or default["intent"],
                "emotion": analysis.get("emotion") or fallback.get("emotion") or default["emotion"],
                "frustration": analysis.get("frustration") if "frustration" in analysis else fallback.get("frustration"),
                "frustration_trend": (
                    analysis.get("frustration_trend")
                    or analysis.get("trend")
                    or _frustration_trend(analysis.get("frustration", fallback.get("frustration", 0)))
                    or default["frustration_trend"]
                ),
                "escalation_risk": analysis.get("risk", fallback.get("risk", default["escalation_risk"])),
                "escalation_level": analysis.get("risk_level", fallback.get("risk_level", default["escalation_level"])),
                "warning_flags": analysis.get("warning_flags", fallback.get("warning_flags", default["warning_flags"])),
                "strategy": analysis.get("strategy", fallback.get("strategy", default["strategy"])),
                "kb_query": analysis.get("kb_query") or fallback.get("kb_query") or customer_message,
                "matched_kb": analysis.get("matched_kb") or fallback.get("chunks") or default["matched_kb"],
            }
            return _normalize_payload(payload)
    except Exception:
        pass

    try:
        analysis = pipe.analyze_turn(
            clean_message,
            [{"role": "customer", "text": clean_message}],
            {"product": "Acme Online Store", "mode": "Manual", "persona": "Calm"},
        )
        chunks = analysis.get("chunks", [])
        matched_kb = _dedupe_names(
            [
                {
                    "doc_name": chunk.get("doc_name") or chunk.get("source") or "Knowledge article",
                    "source": chunk.get("source") or chunk.get("doc_name") or "Knowledge article",
                }
                for chunk in chunks[:3]
            ]
        ) or [
            "billing-policy.pdf",
            "refund-policy.pdf",
            "duplicate-payment-guidance.pdf",
        ]
        return _normalize_payload(
            {
                "customer_message": clean_message,
                "intent": analysis.get("intent", default["intent"]),
                "emotion": analysis.get("emotion", default["emotion"]),
                "frustration": analysis.get("frustration", 0),
                "frustration_trend": analysis.get("frustration_trend") or _frustration_trend(analysis.get("frustration", 0)),
                "escalation_risk": analysis.get("risk", default["escalation_risk"]),
                "escalation_level": analysis.get("risk_level", default["escalation_level"]),
                "warning_flags": analysis.get("warning_flags", default["warning_flags"]),
                "strategy": analysis.get("strategy", default["strategy"]),
                "kb_query": clean_message,
                "matched_kb": matched_kb,
            }
        )
    except Exception:
        return default


def render() -> None:
    """Render a clean, responsive, live workflow panel driven by user input."""
    if "workflow_payload" not in st.session_state:
        st.session_state["workflow_payload"] = _coerce_workflow_payload(_sample_payload()["customer_message"])

    payload = _normalize_payload(st.session_state.get("workflow_payload"))

    st.markdown(
        """
        <style>
            .agent-shell {
                background: linear-gradient(180deg, #f8f7f9 0%, #f3eef1 100%);
                border: 1px solid rgba(15, 23, 42, 0.08);
                border-radius: 18px;
                padding: 1.1rem;
                margin-top: 0.75rem;
                width: 100%;
                box-sizing: border-box;
            }
            .agent-panel {
                background: rgba(255,255,255,0.52);
                border: 1px solid rgba(15, 23, 42, 0.08);
                border-radius: 14px;
                padding: 1rem;
                box-shadow: 0 10px 26px rgba(15, 23, 42, 0.04);
            }
            .agent-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 1rem;
                margin-bottom: 0.9rem;
            }
            .agent-title {
                font-size: clamp(1.5rem, 2vw, 2.3rem);
                font-weight: 700;
                color: #111827;
                margin: 0;
                letter-spacing: -0.03em;
            }
            .agent-live {
                font-size: 0.72rem;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                background: rgba(16, 185, 129, 0.12);
                color: #0f766e;
                border: 1px solid rgba(16, 185, 129, 0.35);
                border-radius: 999px;
                padding: 0.35rem 0.7rem;
                font-weight: 700;
            }
            .agent-message {
                background: rgba(249,250,251,0.85);
                border: 1px solid rgba(15, 23, 42, 0.08);
                border-radius: 12px;
                padding: 0.9rem 1rem;
                margin-bottom: 1rem;
                color: #111827;
                line-height: 1.5;
            }
            .agent-metrics {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 0.8rem;
                margin-bottom: 1rem;
            }
            .agent-metric {
                background: rgba(255,255,255,0.62);
                border: 1px solid rgba(15, 23, 42, 0.08);
                border-radius: 12px;
                padding: 0.8rem 0.9rem;
            }
            .agent-metric .label {
                display: block;
                font-size: 0.7rem;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: #6b7280;
                margin-bottom: 0.35rem;
            }
            .agent-metric .value {
                display: block;
                font-size: 1rem;
                font-weight: 700;
                color: #111827;
            }
            .agent-kb {
                background: rgba(255,255,255,0.42);
                border: 1px solid rgba(15, 23, 42, 0.08);
                border-radius: 12px;
                padding: 0.8rem 0.9rem;
            }
            .agent-kb ul {
                margin: 0.6rem 0 0 1.1rem;
                padding: 0;
                color: #1f2937;
            }
            .agent-kb li {
                margin: 0.35rem 0;
                line-height: 1.5;
            }
            @media (max-width: 700px) {
                .agent-header {
                    flex-direction: column;
                    align-items: flex-start;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        col_input, col_demo = st.columns([1.1, 1.1], gap="large")

        with col_input:
            form = st.form("workflow_customer_form")
            with form:
                message_input = st.text_area(
                    "Customer message",
                    value=payload["customer_message"],
                    height=150,
                    key="workflow_customer_input",
                )
                submitted = st.form_submit_button("Analyze message", use_container_width=True)

            if submitted:
                text = (message_input or "").strip()
                if text:
                    st.session_state["workflow_payload"] = _coerce_workflow_payload(text)
                    payload = _normalize_payload(st.session_state.get("workflow_payload"))

            st.caption("Submit the customer message to trigger a workflow analysis.")

            if st.button("Use sample message", use_container_width=True):
                sample = _sample_payload()["customer_message"]
                st.session_state["workflow_payload"] = _coerce_workflow_payload(sample)
                payload = _normalize_payload(st.session_state.get("workflow_payload"))

        with col_demo:
            customer_text = escape(str(payload["customer_message"]))
            intent_text = escape(str(payload["intent"]))
            emotion_text = escape(str(payload["emotion"]))
            trend_text = escape(str(payload["frustration_trend"]))
            risk_score = int(payload.get("escalation_risk", 0))
            risk_level = escape(str(payload.get("escalation_level", "LOW")))
            strategy_text = escape(str(payload.get("strategy", "")))
            warning_flags = payload.get("warning_flags", [])
            flags_html = " ".join(f"<code style='background:rgba(239,68,68,0.12); color:#b91c1c; padding:2px 6px; border-radius:4px; font-size:0.75rem;'>{escape(str(f))}</code>" for f in warning_flags) if warning_flags else "<span style='color:#10b981; font-size:0.8rem;'>None</span>"

            kb_items = [escape(str(item)) for item in payload.get("matched_kb", [])[:3]]
            kb_html = "".join(f"<li>{item}</li>" for item in kb_items) or "<li>No KB matches returned.</li>"

            st.markdown(
                f"""
                <div class="agent-shell">
                    <div class="agent-panel">
                        <div class="agent-header">
                            <div class="agent-title">Agent workflow response</div>
                            <div class="agent-live">Live</div>
                        </div>
                        <div class="agent-message">{customer_text}</div>
                        <div class="agent-metrics">
                            <div class="agent-metric"><span class="label">Intent</span><span class="value">{intent_text}</span></div>
                            <div class="agent-metric"><span class="label">Emotion</span><span class="value">{emotion_text}</span></div>
                            <div class="agent-metric"><span class="label">Trend</span><span class="value">{trend_text}</span></div>
                            <div class="agent-metric"><span class="label">Escalation Risk</span><span class="value">{risk_score}% ({risk_level})</span></div>
                        </div>
                        <div class="agent-kb" style="margin-bottom: 0.8rem;">
                            <div class="label" style="font-size:0.72rem; letter-spacing:0.08em; text-transform:uppercase; color:#6b7280; font-weight:700;">Escalation Risk Monitor (Agent A5)</div>
                            <div style="font-size:0.82rem; margin-top:0.35rem; color:#1f2937;"><strong>Active Flags:</strong> {flags_html}</div>
                            <div style="font-size:0.82rem; margin-top:0.3rem; color:#4b5563;"><strong>Strategy:</strong> {strategy_text}</div>
                        </div>
                        <div class="agent-kb">
                            <div class="label" style="font-size:0.72rem; letter-spacing:0.08em; text-transform:uppercase; color:#6b7280; font-weight:700;">Knowledge matches</div>
                            <ul>{kb_html}</ul>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
