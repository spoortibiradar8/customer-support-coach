"""Escalation Risk Monitor Agent input and output schemas.

Provides strict Pydantic v2 data contracts for the Escalation Risk Monitor
Agent, supporting multi-level risk scoring, warning flags, sentiment trajectory
tracking, de-escalation guidance, and seamless integration with the shared
orchestrator and AgentResult data models.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.orchestrator.knowledge_schemas import ConversationHistoryItem


class EscalationRiskLevel(str, Enum):
    """Categorical classification of escalation severity."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EscalationSeverity(str, Enum):
    """Severity rating for individual detected escalation warning flags."""

    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class EscalationFlag(BaseModel):
    """Structured record of an identified escalation indicator."""

    model_config = ConfigDict(extra="ignore")

    code: str = Field(
        ...,
        description="Machine-readable flag identifier, e.g. 'CHURN_THREAT', 'SUPERVISOR_REQUEST'.",
    )
    severity: EscalationSeverity = Field(
        default=EscalationSeverity.WARNING,
        description="Severity weighting for this specific indicator.",
    )
    description: str = Field(
        ...,
        description="Human-readable explanation of why this flag was triggered.",
    )
    matched_cues: list[str] = Field(
        default_factory=list,
        description="Specific keywords or phrases from the dialogue that triggered the flag.",
    )


class EscalationRiskRequest(BaseModel):
    """Input contract for the Escalation Risk Monitor Agent.

    Required fields:
        - message: Latest customer message or interaction text.

    Optional fields:
        - history: Conversation history turns for trajectory and context analysis.
        - session_id: Identifier of the active coaching session.
        - frustration_score: Frustration percentage score (0-100) from upstream telemetry.
        - turn_count: Cumulative number of customer turns in this conversation.
        - customer_type: Persona or behavior profile (e.g. 'Demanding', 'Calm').
        - product: Product or service context.
        - metadata: Additional session-level metadata.
    """

    model_config = ConfigDict(extra="ignore")

    message: str = Field(
        ...,
        min_length=1,
        description="Incoming customer turn text to evaluate for escalation signals.",
    )
    history: list[ConversationHistoryItem] = Field(
        default_factory=list,
        description="Prior conversation turns for sentiment trajectory and repeat-contact tracking.",
    )
    session_id: str | None = Field(
        default=None,
        max_length=128,
        description="Active session identifier (1-128 valid ID characters).",
    )
    frustration_score: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Upstream frustration score (0-100%).",
    )
    turn_count: int | None = Field(
        default=None,
        ge=0,
        description="Total customer turns so far in this session.",
    )
    customer_type: str | None = Field(
        default=None,
        description="Customer persona or temperament (e.g. 'Demanding', 'Frustrated', 'Calm').",
    )
    product: str | None = Field(
        default=None,
        description="Product or service context.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context attributes.",
    )

    @field_validator("message", mode="before")
    @classmethod
    def message_must_not_be_whitespace(cls, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Customer message must not be empty or whitespace-only.")
        return value.strip()

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        clean = value.strip()
        if not clean:
            return None
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", clean):
            raise ValueError(
                "session_id must contain 1-128 valid ID characters (letters, digits, _.:-)."
            )
        return clean

    @field_validator("history", mode="before")
    @classmethod
    def coerce_history(cls, raw: Any) -> Any:
        """Tolerantly accept list of dicts or ConversationHistoryItem instances."""
        if not isinstance(raw, list):
            return raw
        normalized = []
        for item in raw:
            if hasattr(item, "to_dict"):
                item = item.to_dict()
            if isinstance(item, dict):
                speaker = item.get("speaker") or item.get("role") or "customer"
                content = item.get("content") or item.get("text") or ""
                turn = item.get("turn_number") or item.get("turn")
                normalized.append({
                    "speaker": speaker,
                    "content": content,
                    "turn_number": turn,
                })
            else:
                normalized.append(item)
        return normalized


class EscalationRiskResponse(BaseModel):
    """Output contract for the Escalation Risk Monitor Agent.

    Contains calibrated escalation risk score, risk tier, sentiment trajectory,
    identified warning flags, plain-text reasons, recommended de-escalation
    strategy, and supervisor/tier-2 eligibility.
    """

    model_config = ConfigDict(extra="ignore")

    agent_name: str = Field(
        default="EscalationRiskMonitorAgent",
        description="Identifier of the executing agent.",
    )
    status: Literal["success", "error"] = Field(
        default="success",
        description="Execution status.",
    )
    risk_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Calibrated escalation probability percentage (0–100%).",
    )
    risk_level: EscalationRiskLevel = Field(
        ...,
        description="Categorical risk tier: 'low', 'medium', 'high', or 'critical'.",
    )
    frustration_trend: Literal["falling", "stable", "rising", "spike"] = Field(
        default="stable",
        description="Sentiment/frustration velocity across recent turns.",
    )
    warning_flags: list[str] = Field(
        default_factory=list,
        description="List of active warning flag codes.",
    )
    flag_details: list[EscalationFlag] = Field(
        default_factory=list,
        description="Detailed structured records of all triggered flags.",
    )
    reasons: list[str] = Field(
        default_factory=list,
        description="Human-readable explanations justifying the risk score.",
    )
    recommended_strategy: str = Field(
        ...,
        description="Context-specific de-escalation playbook and next-action guidance.",
    )
    requires_supervisor: bool = Field(
        default=False,
        description="Whether immediate supervisor handover is advised.",
    )
    tier2_eligible: bool = Field(
        default=False,
        description="Whether issue qualifies for Tier-2 / engineering incident escalation.",
    )
    suggested_de_escalation_phrase: str = Field(
        default="",
        description="Recommended calming phrase the agent can use immediately.",
    )
    error: str | None = Field(
        default=None,
        description="Error details if execution encountered a failure.",
    )
    session_id: str | None = Field(
        default=None,
        description="Associated session identifier.",
    )

    @classmethod
    def create_success(
        cls,
        risk_score: int,
        risk_level: EscalationRiskLevel,
        frustration_trend: Literal["falling", "stable", "rising", "spike"],
        warning_flags: list[str],
        flag_details: list[EscalationFlag],
        reasons: list[str],
        recommended_strategy: str,
        requires_supervisor: bool = False,
        tier2_eligible: bool = False,
        suggested_de_escalation_phrase: str = "",
        session_id: str | None = None,
        agent_name: str = "EscalationRiskMonitorAgent",
    ) -> EscalationRiskResponse:
        """Factory for a successful escalation risk monitoring response."""
        return cls(
            agent_name=agent_name,
            status="success",
            risk_score=max(0, min(100, risk_score)),
            risk_level=risk_level,
            frustration_trend=frustration_trend,
            warning_flags=warning_flags,
            flag_details=flag_details,
            reasons=reasons,
            recommended_strategy=recommended_strategy,
            requires_supervisor=requires_supervisor,
            tier2_eligible=tier2_eligible,
            suggested_de_escalation_phrase=suggested_de_escalation_phrase,
            session_id=session_id,
            error=None,
        )

    @classmethod
    def create_error(
        cls,
        error_message: str,
        session_id: str | None = None,
        agent_name: str = "EscalationRiskMonitorAgent",
    ) -> EscalationRiskResponse:
        """Factory for an error response."""
        return cls(
            agent_name=agent_name,
            status="error",
            risk_score=0,
            risk_level=EscalationRiskLevel.LOW,
            frustration_trend="stable",
            warning_flags=["AGENT_ERROR"],
            flag_details=[
                EscalationFlag(
                    code="AGENT_ERROR",
                    severity=EscalationSeverity.INFO,
                    description=error_message,
                )
            ],
            reasons=[error_message],
            recommended_strategy="Proceed with standard resolution.",
            requires_supervisor=False,
            tier2_eligible=False,
            suggested_de_escalation_phrase="",
            session_id=session_id,
            error=error_message,
        )

    def to_agent_result(self, session_id: str | None = None) -> Any:
        """Export to the shared AgentResult dataclass for orchestrator compatibility."""
        from backend.core.data_models import AgentResult

        sid = session_id or self.session_id or "sess-default"
        return AgentResult(
            session_id=sid,
            agent_type=self.agent_name,
            result=self.model_dump(),
        )
