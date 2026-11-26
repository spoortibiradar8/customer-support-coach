"""Escalation Risk Monitor Agent.

Member of the Specialized Agent Ecosystem (Agent A5 / Risk Mitigation layer).
Tracks sentiment trajectory across conversation turns to detect churn threats,
explicit supervisor demands, repeated contact friction, SLA breaches, and legal
or financial liabilities, providing real-time escalation risk scores and
actionable de-escalation playbooks.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

from backend.core.data_models import AgentResult, Session
from backend.orchestrator.escalation_schemas import (
    EscalationFlag,
    EscalationRiskLevel,
    EscalationRiskRequest,
    EscalationRiskResponse,
    EscalationSeverity,
)

logger = logging.getLogger(__name__)

# Pattern dictionaries for multi-dimensional escalation signal detection
PATTERNS: dict[str, dict[str, Any]] = {
    "SUPERVISOR_REQUEST": {
        "severity": EscalationSeverity.CRITICAL,
        "weight": 35,
        "description": "Explicit demand for supervisor, manager, lead, or Tier-2 support.",
        "regex": r"\b(speak to|talk to|speak with|talk with|transfer( me)? to|get me|give me|connect me with|escalate to|need a|want a|call a)\s+(a\s+|my\s+|your\s+|the\s+)?(supervisor|manager|lead|tier\s*2|higher\s*up|director|boss|someone in charge|level 2|team lead)\b|\b(escalate this|formal escalation|tier\s*2\s*support)\b|\b(transfer me to.*(supervisor|manager|lead))\b|\b(get me a manager|want a manager)\b",
    },
    "CHURN_THREAT": {
        "severity": EscalationSeverity.HIGH,
        "weight": 25,
        "description": "Customer threatening cancellation, switching to a competitor, or closing account.",
        "regex": r"\b(cancel(ling)? (my\s+)?(order|account|subscription|service|membership)|close (my\s+)?account|switch(ing)? to (a\s+)?competitor|take my business elsewhere|never buy(ing)? again|never shop(ping)? here again|stop using|done with you(r company)?|unsubscribe)\b",
    },
    "LEGAL_REGULATORY_THREAT": {
        "severity": EscalationSeverity.CRITICAL,
        "weight": 40,
        "description": "Threat of legal action, regulatory complaints, or consumer protection reporting.",
        "regex": r"\b(lawyer|attorney|legal action|take legal|sue you|take (you|this) to court|small claims|better business bureau|\bbbb\b|consumer protection|consumer affairs|\bftc\b|\bfcc\b|regulator|regulatory agency|police|report you|contact authorities)\b",
    },
    "FINANCIAL_FRAUD_DISPUTE": {
        "severity": EscalationSeverity.HIGH,
        "weight": 25,
        "description": "Severe financial dispute, fraud allegation, chargeback, or unauthorized billing.",
        "regex": r"\b(unauthorized charge|credit card dispute|bank dispute|chargeback|stolen money|fraud|fraudulent|robbery|scam|scammed|ripoff|rip-off|stealing|double charged|charged twice|illegal charge)\b",
    },
    "SLA_TIME_CRITICALITY": {
        "severity": EscalationSeverity.WARNING,
        "weight": 15,
        "description": "Extreme urgency, deadline breach, emergency, or business impact.",
        "regex": r"\b(asap|immediately|urgent|urgently|emergency|critical|deadline|hours waiting|waiting for days|costing me money|business critical|production down|system down|time-sensitive)\b",
    },
    "ABUSIVE_OR_EXTREME_FRUSTRATION": {
        "severity": EscalationSeverity.HIGH,
        "weight": 20,
        "description": "High emotional intensity, shouting (caps), or severe negative sentiment.",
        "regex": r"\b(unacceptable|ridiculous|disgusting|horrible|terrible|atrocious|pathetic|incompetent|worst (customer )?service|utter nonsense|lied to me|complete waste of time)\b",
    },
}

NEGATIVE_WORDS = {
    "bad", "terrible", "horrible", "awful", "worst", "unacceptable", "ridiculous",
    "disgusted", "angry", "furious", "broken", "useless", "incompetent", "waste",
    "failure", "hate", "problem", "wrong", "delay", "delayed", "poor", "frustrated",
    "frustrating", "lied", "lying", "cheat", "scam", "shame", "issue", "damaged",
}

POSITIVE_WORDS = {
    "good", "great", "thank", "thanks", "helpful", "perfect", "resolved",
    "appreciate", "awesome", "excellent", "glad", "satisfied", "wonderful",
}


def _estimate_turn_frustration(text: str) -> int:
    """Compute heuristic frustration score (0-100) for a single customer text."""
    lower = text.lower()
    words = re.findall(r"\b[a-z]+\b", lower)
    neg_count = sum(1 for w in words if w in NEGATIVE_WORDS)
    pos_count = sum(1 for w in words if w in POSITIVE_WORDS)

    score = 20 + (neg_count * 12) - (pos_count * 20)

    # Exclamation mark emphasis
    exclamation_count = text.count("!")
    if exclamation_count >= 2:
        score += min(20, exclamation_count * 6)

    # All-caps detection for words >= 3 chars
    upper_words = [w for w in text.split() if len(w) >= 3 and w.isupper() and w.isalpha()]
    if len(upper_words) >= 2:
        score += min(25, len(upper_words) * 8)

    # Pattern triggers that immediately boost emotional temperature
    if re.search(r"\b(unacceptable|ridiculous|terrible|worst|scam|lied|fraud|unauthorized|stolen)\b", lower):
        score += 15

    return max(0, min(100, score))


def _calculate_frustration_trend(
    history: list[ConversationHistoryItem],
    current_frustration: int,
) -> tuple[Literal["falling", "stable", "rising", "spike"], list[int]]:
    """Determine emotional trajectory across turns (falling, stable, rising, or spike)."""
    past_scores: list[int] = []
    for item in history:
        speaker = getattr(item, "speaker", None)
        if speaker is None and isinstance(item, dict):
            speaker = item.get("speaker") or item.get("role")
        if str(speaker).lower() in ("customer", "user"):
            content = getattr(item, "content", None)
            if content is None and isinstance(item, dict):
                content = item.get("content") or item.get("text")
            if content and str(content).strip():
                past_scores.append(_estimate_turn_frustration(str(content)))

    all_scores = past_scores + [current_frustration]
    if len(all_scores) < 2:
        if current_frustration >= 75:
            return "rising", all_scores
        return "stable", all_scores

    prev_score = all_scores[-2]
    delta = current_frustration - prev_score

    if delta >= 30:
        return "spike", all_scores
    if delta >= 12 or (len(all_scores) >= 3 and all_scores[-1] > all_scores[-2] > all_scores[-3]):
        return "rising", all_scores
    if delta <= -12 or (len(all_scores) >= 3 and all_scores[-1] < all_scores[-2] < all_scores[-3]):
        return "falling", all_scores
    return "stable", all_scores


class EscalationRiskMonitorAgent:
    """Escalation Risk Monitor Agent (A5).

    Evaluates live dialogue streams to forecast churn threats, manager demands,
    repeated contact fatigue, and SLA violations, generating structured warning
    flags and de-escalation strategies.
    """

    AGENT_TYPE = "escalation-risk-monitor-agent"
    HIGH_RISK_THRESHOLD = 70
    CRITICAL_RISK_THRESHOLD = 86

    def __init__(
        self,
        high_risk_threshold: int = HIGH_RISK_THRESHOLD,
        critical_risk_threshold: int = CRITICAL_RISK_THRESHOLD,
    ) -> None:
        self.high_risk_threshold = high_risk_threshold
        self.critical_risk_threshold = critical_risk_threshold

    def analyze(self, request: EscalationRiskRequest) -> EscalationRiskResponse:
        """Analyze customer turn and dialogue context for escalation risks."""
        text = request.message.strip()
        lower_text = text.lower()

        # 1. Frustration calculation & trajectory
        current_frustration = (
            request.frustration_score
            if request.frustration_score is not None
            else _estimate_turn_frustration(text)
        )
        trend, score_series = _calculate_frustration_trend(request.history, current_frustration)

        # 2. Count customer turns
        past_cust_turns = sum(
            1
            for item in request.history
            if getattr(item, "speaker", str(item.get("role") if isinstance(item, dict) else "")).lower()
            in ("customer", "user")
        )
        total_cust_turns = (request.turn_count or (past_cust_turns + 1))

        # 3. Pattern Matching for Warning Flags
        triggered_flags: list[EscalationFlag] = []
        flag_weights: int = 0
        reasons: list[str] = []

        for code, meta in PATTERNS.items():
            matches = list(re.finditer(meta["regex"], lower_text))
            if matches:
                matched_cues = sorted({m.group(0).strip() for m in matches})
                flag = EscalationFlag(
                    code=code,
                    severity=meta["severity"],
                    description=meta["description"],
                    matched_cues=matched_cues,
                )
                triggered_flags.append(flag)
                flag_weights += meta["weight"]
                cue_str = f" ('{matched_cues[0]}')" if matched_cues else ""
                reasons.append(f"{meta['description']}{cue_str}")

        # 4. Repeat Contact / Customer Fatigue Detection
        if total_cust_turns >= 3 and current_frustration >= 40:
            repeat_flag = EscalationFlag(
                code="REPEAT_CONTACT_FATIGUE",
                severity=EscalationSeverity.WARNING if total_cust_turns < 5 else EscalationSeverity.HIGH,
                description=f"Customer has contacted repeatedly ({total_cust_turns} turns) without full resolution.",
                matched_cues=[f"turn_count={total_cust_turns}"],
            )
            triggered_flags.append(repeat_flag)
            flag_weights += 15 if total_cust_turns < 5 else 25
            reasons.append(f"Customer has contacted repeatedly ({total_cust_turns} turns) without full resolution.")

        # 5. Trajectory Momentum Risk Adjustment
        trajectory_bonus = 0
        if trend == "spike":
            trajectory_bonus = 18
            reasons.append("Sudden emotional escalation spike detected between turns.")
        elif trend == "rising":
            trajectory_bonus = 10
            reasons.append("Frustration trajectory is rising across conversation turns.")
        elif trend == "falling":
            trajectory_bonus = -15
            reasons.append("Customer is de-escalating and emotional intensity is decreasing.")

        # 6. Persona Adjustment
        persona_bonus = 0
        cust_type = (request.customer_type or "").lower()
        if "demanding" in cust_type:
            persona_bonus = 8
        elif "frustrated" in cust_type or "angry" in cust_type:
            persona_bonus = 10

        # 7. Composite Calibrated Risk Score Calculation
        # Base risk anchored on emotional frustration
        base_risk = current_frustration * 0.65
        composite_score = int(round(base_risk + flag_weights + trajectory_bonus + persona_bonus))

        # Absolute rule floors:
        # - Legal threat guarantees at least 88%
        # - Supervisor demand guarantees at least 78%
        # - Churn threat guarantees at least 70%
        flag_codes = {f.code for f in triggered_flags}
        if "LEGAL_REGULATORY_THREAT" in flag_codes:
            composite_score = max(composite_score, 88)
        if "SUPERVISOR_REQUEST" in flag_codes:
            composite_score = max(composite_score, 78)
        if "CHURN_THREAT" in flag_codes:
            composite_score = max(composite_score, 70)
        if "FINANCIAL_FRAUD_DISPUTE" in flag_codes:
            composite_score = max(composite_score, 50)

        calibrated_score = max(0, min(100, composite_score))

        # 8. Determine Risk Level
        if calibrated_score >= self.critical_risk_threshold:
            risk_level = EscalationRiskLevel.CRITICAL
        elif calibrated_score >= self.high_risk_threshold:
            risk_level = EscalationRiskLevel.HIGH
        elif calibrated_score >= 35:
            risk_level = EscalationRiskLevel.MEDIUM
        else:
            risk_level = EscalationRiskLevel.LOW

        # 9. Determine Supervisor / Tier-2 Handover Need
        requires_supervisor = (
            calibrated_score >= self.high_risk_threshold
            or "SUPERVISOR_REQUEST" in flag_codes
            or "LEGAL_REGULATORY_THREAT" in flag_codes
        )
        tier2_eligible = (
            "SUPERVISOR_REQUEST" in flag_codes
            or "SLA_TIME_CRITICALITY" in flag_codes
            or "FINANCIAL_FRAUD_DISPUTE" in flag_codes
            or total_cust_turns >= 4
        )

        # 10. Generate Targeted De-escalation Strategy and Phrase
        recommended_strategy, suggested_phrase = self._build_guidance(
            risk_level=risk_level,
            flag_codes=flag_codes,
            total_cust_turns=total_cust_turns,
            product=request.product,
        )

        if not reasons:
            reasons.append("No strong escalation signals; sentiment is manageable.")

        return EscalationRiskResponse.create_success(
            risk_score=calibrated_score,
            risk_level=risk_level,
            frustration_trend=trend,
            warning_flags=[f.code for f in triggered_flags],
            flag_details=triggered_flags,
            reasons=reasons,
            recommended_strategy=recommended_strategy,
            requires_supervisor=requires_supervisor,
            tier2_eligible=tier2_eligible,
            suggested_de_escalation_phrase=suggested_phrase,
            session_id=request.session_id,
            agent_name=self.AGENT_TYPE,
        )

    def _build_guidance(
        self,
        risk_level: EscalationRiskLevel,
        flag_codes: set[str],
        total_cust_turns: int,
        product: str | None,
    ) -> tuple[str, str]:
        """Produce actionable de-escalation guidance and verbatim phrase."""
        prod = product or "our service"

        if "LEGAL_REGULATORY_THREAT" in flag_codes:
            strategy = (
                "CRITICAL COMPLIANCE THREAT: Do not debate, cite fine print, or argue liability. "
                "Remain calm, document the customer's exact complaint verbatim, and immediately offer "
                "formal escalation to our legal affairs / executive escalations team."
            )
            phrase = (
                "I take your concerns very seriously. I want to make sure this is handled with the highest "
                "priority, so I am documenting your case directly for our senior escalations team."
            )
            return strategy, phrase

        if "SUPERVISOR_REQUEST" in flag_codes:
            strategy = (
                "SUPERVISOR REQUEST DETECTED: Acknowledge the request directly without avoidance or "
                "defensiveness. Inform the customer you can connect them with a supervisor immediately, "
                "while offering to begin resolving the issue in parallel."
            )
            phrase = (
                "I completely respect your request to speak with a supervisor. While I prepare the transfer "
                "and brief my lead on your situation, may I review your details so they have full context?"
            )
            return strategy, phrase

        if "CHURN_THREAT" in flag_codes:
            strategy = (
                "CHURN RISK ALERT: Customer is threatening to cancel or defect. Prioritize retention: "
                "validate their frustration, take personal responsibility, and provide an immediate "
                "concrete resolution or compensatory concession before discussing policy limits."
            )
            phrase = (
                f"We truly value your business with {prod}, and I am deeply sorry for this experience. "
                "I will personally take ownership to make this right for you immediately."
            )
            return strategy, phrase

        if "REPEAT_CONTACT_FATIGUE" in flag_codes or total_cust_turns >= 4:
            strategy = (
                "REPEAT CONTACT FATIGUE: Customer is frustrated from repeating themselves across multiple turns. "
                "Acknowledge the repeated effort, do NOT ask them to repeat information already shared, "
                "and provide an explicit resolution timeline."
            )
            phrase = (
                f"I realize this is your {total_cust_turns}th message regarding this issue, and I apologize "
                "for the continued back-and-forth. You have my full attention to get this solved now."
            )
            return strategy, phrase

        if risk_level in (EscalationRiskLevel.HIGH, EscalationRiskLevel.CRITICAL):
            strategy = (
                "HIGH ESCALATION RISK: Acknowledge feelings with deep empathy, own the issue, "
                "offer a clear timeline, and inform the customer that a supervisor is on standby."
            )
            phrase = (
                "I completely understand how frustrating this has been, and I apologize. "
                "Let's resolve this step by step right now."
            )
            return strategy, phrase

        if risk_level == EscalationRiskLevel.MEDIUM:
            strategy = (
                "MODERATE FRICTION: Maintain warm, attentive tone. Confirm exact understanding of the issue "
                "and clearly outline the next action step to prevent escalation."
            )
            phrase = (
                "Thank you for sharing those details. Here is exactly what I will do to resolve this for you."
            )
            return strategy, phrase

        return (
            "STABLE INTERACTION: Sentiment is manageable. Proceed with standard policy resolution.",
            "I'm glad to help you with this today.",
        )

    def monitor(
        self,
        message: str,
        history: list[Any] | None = None,
        session_id: str | None = None,
        frustration_score: int | None = None,
        turn_count: int | None = None,
        customer_type: str | None = None,
        product: str | None = None,
    ) -> EscalationRiskResponse:
        """Convenience monitor method accepting raw primitives."""
        req = EscalationRiskRequest(
            message=message,
            history=history or [],
            session_id=session_id,
            frustration_score=frustration_score,
            turn_count=turn_count,
            customer_type=customer_type,
            product=product,
        )
        return self.analyze(req)

    def run(self, session: Session, message: str, **kwargs: Any) -> AgentResult:
        """Standard orchestrator agent entry point: agent.run(session, message) -> AgentResult."""
        session_id = getattr(session, "session_id", "sess-default") or "sess-default"
        clean_msg = (message or "").strip()

        if not clean_msg:
            resp = EscalationRiskResponse.create_error(
                error_message="Cannot evaluate empty message for escalation risk.",
                session_id=session_id,
                agent_name=self.AGENT_TYPE,
            )
            return resp.to_agent_result(session_id=session_id)

        try:
            # Extract history from session if available
            raw_history = (
                getattr(session, "replay_transcript", None)
                or getattr(session, "messages", None)
                or []
            )
            product = getattr(session, "product", None)
            customer_type = getattr(session, "persona", None) or getattr(session, "customer_type", None)

            req = EscalationRiskRequest(
                message=clean_msg,
                history=raw_history,
                session_id=session_id,
                customer_type=str(customer_type) if customer_type else None,
                product=str(product) if product else None,
            )
            response = self.analyze(req)
        except Exception as exc:
            logger.exception("Escalation risk monitor execution failed")
            response = EscalationRiskResponse.create_error(
                error_message=f"Escalation monitor error: {exc}",
                session_id=session_id,
                agent_name=self.AGENT_TYPE,
            )

        return response.to_agent_result(session_id=session_id)
