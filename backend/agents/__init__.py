"""Agent implementations package.

Contains agent implementations for the Customer Support Coach platform,
including the Knowledge Recommendation Agent, Coaching & Response Suggestion Agent,
and Escalation Risk Monitor Agent.
"""

from backend.agents.coaching_agent import CoachingResponseAgent
from backend.agents.escalation_agent import EscalationRiskMonitorAgent
from backend.agents.knowledge_agent import KnowledgeRecommendationAgent

__all__ = [
    "CoachingResponseAgent",
    "EscalationRiskMonitorAgent",
    "KnowledgeRecommendationAgent",
]
