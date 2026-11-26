"""Unit and contract tests for the Escalation Risk Monitor Agent.

Tests cover:
- Low-risk standard customer inquiries
- Explicit supervisor / manager handover demands
- Churn and subscription cancellation threats
- Legal and regulatory / consumer affairs warnings
- Severe financial fraud / chargeback disputes
- Repeat contact fatigue and multi-turn friction
- Frustration trajectory tracking (spike, rising, falling)
- Orchestrator agent contract compliance (AgentResult)
- Pydantic schema validation and error resilience
- Integration through pipeline_stub.analyze_turn
"""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.agents.escalation_agent import EscalationRiskMonitorAgent
from backend.core.data_models import AgentResult, Session
from backend.orchestrator.escalation_schemas import (
    EscalationFlag,
    EscalationRiskLevel,
    EscalationRiskRequest,
    EscalationRiskResponse,
    EscalationSeverity,
)
from backend.services import pipeline_stub


@pytest.fixture
def escalation_agent():
    """A fresh instance of EscalationRiskMonitorAgent."""
    return EscalationRiskMonitorAgent()


# ---------------------------------------------------------------------------
# 1. Low Risk Standard Inquiry
# ---------------------------------------------------------------------------

def test_low_risk_polite_inquiry(escalation_agent):
    """Calm, polite question receives low risk score and LOW level."""
    req = EscalationRiskRequest(
        message="Hello! Could you please help me check the status of my order?",
        customer_type="Calm",
    )
    resp = escalation_agent.analyze(req)

    assert resp.status == "success"
    assert resp.risk_level == EscalationRiskLevel.LOW
    assert resp.risk_score <= 35
    assert resp.requires_supervisor is False
    assert len(resp.warning_flags) == 0


# ---------------------------------------------------------------------------
# 2. Explicit Supervisor Escalation Demand
# ---------------------------------------------------------------------------

def test_explicit_supervisor_demand(escalation_agent):
    """Demand to speak to a manager triggers SUPERVISOR_REQUEST flag and high risk."""
    req = EscalationRiskRequest(
        message="I have had enough of this. Transfer me to your supervisor or manager right now!",
        customer_type="Frustrated",
    )
    resp = escalation_agent.analyze(req)

    assert resp.status == "success"
    assert "SUPERVISOR_REQUEST" in resp.warning_flags
    assert resp.risk_score >= 78
    assert resp.requires_supervisor is True
    assert "SUPERVISOR REQUEST DETECTED" in resp.recommended_strategy
    assert any("supervisor" in f.code.lower() or "supervisor" in f.description.lower() for f in resp.flag_details)


# ---------------------------------------------------------------------------
# 3. Churn & Cancellation Threat
# ---------------------------------------------------------------------------

def test_churn_and_cancellation_threat(escalation_agent):
    """Threat to cancel account/switch to competitor triggers CHURN_THREAT flag."""
    req = EscalationRiskRequest(
        message="Your service is terrible. Cancel my subscription immediately, I will take my business elsewhere!",
        product="Acme Cloud",
    )
    resp = escalation_agent.analyze(req)

    assert resp.status == "success"
    assert "CHURN_THREAT" in resp.warning_flags
    assert resp.risk_score >= 70
    assert "CHURN RISK ALERT" in resp.recommended_strategy
    assert "Acme Cloud" in resp.suggested_de_escalation_phrase


# ---------------------------------------------------------------------------
# 4. Legal & Regulatory / BBB Threat
# ---------------------------------------------------------------------------

def test_legal_and_regulatory_threat(escalation_agent):
    """Threat of legal action or BBB report triggers CRITICAL risk tier."""
    req = EscalationRiskRequest(
        message="If this is not resolved today, I will contact my lawyer and report your company to the Better Business Bureau!",
    )
    resp = escalation_agent.analyze(req)

    assert resp.status == "success"
    assert "LEGAL_REGULATORY_THREAT" in resp.warning_flags
    assert resp.risk_level == EscalationRiskLevel.CRITICAL
    assert resp.risk_score >= 88
    assert resp.requires_supervisor is True
    assert "CRITICAL COMPLIANCE THREAT" in resp.recommended_strategy


# ---------------------------------------------------------------------------
# 5. Financial & Fraud Dispute
# ---------------------------------------------------------------------------

def test_financial_fraud_dispute(escalation_agent):
    """Unauthorized charge and fraud accusations trigger FINANCIAL_FRAUD_DISPUTE flag."""
    req = EscalationRiskRequest(
        message="I noticed an unauthorized charge on my card. You charged twice and this is fraud!",
    )
    resp = escalation_agent.analyze(req)

    assert resp.status == "success"
    assert "FINANCIAL_FRAUD_DISPUTE" in resp.warning_flags
    assert resp.risk_score >= 50
    assert resp.tier2_eligible is True


# ---------------------------------------------------------------------------
# 6. Repeat Contact Fatigue
# ---------------------------------------------------------------------------

def test_repeat_contact_fatigue(escalation_agent):
    """Multiple unresolved customer turns trigger REPEAT_CONTACT_FATIGUE."""
    history = [
        {"role": "customer", "text": "My package hasn't arrived."},
        {"role": "agent", "text": "Please wait another day."},
        {"role": "customer", "text": "Still not here, what is happening?"},
        {"role": "agent", "text": "We are looking into it."},
    ]
    req = EscalationRiskRequest(
        message="This is ridiculous, nobody has fixed my issue and nothing has changed!",
        history=history,
        turn_count=3,
    )
    resp = escalation_agent.analyze(req)

    assert resp.status == "success"
    assert "REPEAT_CONTACT_FATIGUE" in resp.warning_flags
    assert any("repeatedly" in r.lower() for r in resp.reasons)


# ---------------------------------------------------------------------------
# 7. Sentiment Trajectory Tracking
# ---------------------------------------------------------------------------

def test_frustration_trajectory_spike(escalation_agent):
    """Sudden jump in frustration from calm to furious triggers a spike trajectory."""
    history = [
        {"role": "customer", "text": "Thank you, I will check the link."},
    ]
    # Current message is extremely aggressive
    req = EscalationRiskRequest(
        message="THAT DID NOT WORK AT ALL!! THIS IS UNACCEPTABLE AND ATROCIOUS SERVICE!",
        history=history,
    )
    resp = escalation_agent.analyze(req)

    assert resp.frustration_trend in ("spike", "rising")
    assert resp.risk_score >= 60


def test_frustration_trajectory_falling(escalation_agent):
    """Calming customer interaction detects falling trajectory."""
    history = [
        {"role": "customer", "text": "This is ridiculous and broken, I am so angry!"},
        {"role": "agent", "text": "I am so sorry, let me fix this immediately."},
        {"role": "customer", "text": "I am still waiting for the fix..."},
        {"role": "agent", "text": "I have credited your account and shipped the replacement."},
    ]
    req = EscalationRiskRequest(
        message="Great, thank you so much! That works now, I appreciate your help.",
        history=history,
    )
    resp = escalation_agent.analyze(req)

    assert resp.frustration_trend == "falling"
    assert resp.risk_score <= 35
    assert resp.risk_level == EscalationRiskLevel.LOW


# ---------------------------------------------------------------------------
# 8. Orchestrator Contract & AgentResult Compliance
# ---------------------------------------------------------------------------

def test_orchestrator_agent_run_contract(escalation_agent):
    """agent.run(session, message) conforms to standard AgentResult contract."""
    session = Session(session_id="sess-orch-01", product="Gadget Pro")
    result = escalation_agent.run(session, "I want to cancel my order immediately.")

    assert isinstance(result, AgentResult)
    assert result.session_id == "sess-orch-01"
    assert result.agent_type == "escalation-risk-monitor-agent"
    assert isinstance(result.result, dict)
    assert result.result["risk_score"] >= 70
    assert "CHURN_THREAT" in result.result["warning_flags"]


def test_empty_message_run_returns_error_result(escalation_agent):
    """Empty message passed to run() gracefully returns error AgentResult."""
    session = Session(session_id="sess-orch-02")
    result = escalation_agent.run(session, "   ")

    assert isinstance(result, AgentResult)
    assert result.result["status"] == "error"
    assert "AGENT_ERROR" in result.result["warning_flags"]


# ---------------------------------------------------------------------------
# 9. Pydantic Schema Validation
# ---------------------------------------------------------------------------

def test_empty_request_message_raises_validation_error():
    """Empty or whitespace-only message raises ValidationError."""
    with pytest.raises(ValidationError):
        EscalationRiskRequest(message="   ")


def test_invalid_session_id_raises_validation_error():
    """Session ID with invalid characters raises ValidationError."""
    with pytest.raises(ValidationError):
        EscalationRiskRequest(message="Help", session_id="invalid/session/id!")


def test_response_to_agent_result_method():
    """EscalationRiskResponse.to_agent_result exports properly typed AgentResult."""
    resp = EscalationRiskResponse.create_success(
        risk_score=75,
        risk_level=EscalationRiskLevel.HIGH,
        frustration_trend="rising",
        warning_flags=["SUPERVISOR_REQUEST"],
        flag_details=[
            EscalationFlag(
                code="SUPERVISOR_REQUEST",
                severity=EscalationSeverity.CRITICAL,
                description="Supervisor requested",
            )
        ],
        reasons=["Customer asked for supervisor"],
        recommended_strategy="Connect supervisor immediately",
        session_id="sess-test-99",
    )
    agent_res = resp.to_agent_result()

    assert agent_res.session_id == "sess-test-99"
    assert agent_res.agent_type == "EscalationRiskMonitorAgent"
    assert agent_res.result["risk_score"] == 75


# ---------------------------------------------------------------------------
# 10. Pipeline Stub Integration
# ---------------------------------------------------------------------------

def test_pipeline_stub_analyze_turn_includes_escalation_data():
    """pipeline_stub.analyze_turn seamlessly returns all escalation monitor fields."""
    history = [
        {"role": "customer", "text": "I have an issue with my bill."},
        {"role": "agent", "text": "I can help with that."},
    ]
    analysis = pipeline_stub.analyze_turn(
        text="I am sick of waiting! Transfer me to your manager or I am cancelling my subscription!",
        history=history,
        cfg={"product": "SuperHost", "mode": "Simulator", "persona": "Frustrated"},
    )

    # Core backward compatibility keys
    assert "risk" in analysis
    assert "risk_reason" in analysis
    assert "strategy" in analysis
    assert analysis["risk"] >= 75

    # Enhanced Escalation Risk Monitor keys
    assert "risk_level" in analysis
    assert "warning_flags" in analysis
    assert "requires_supervisor" in analysis
    assert analysis["requires_supervisor"] is True
    assert "SUPERVISOR_REQUEST" in analysis["warning_flags"]
    assert "CHURN_THREAT" in analysis["warning_flags"]
    assert "suggested_de_escalation_phrase" in analysis
