import sys
from pathlib import Path

import pytest

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.agents.coaching_agent import CoachingResponseAgent
from backend.core.data_models import AgentResult, Session


@pytest.fixture
def agent():
    """A fresh instance of CoachingResponseAgent."""
    return CoachingResponseAgent()


# 1. Empty representative reply
def test_empty_representative_reply(agent):
    """An empty reply receives a score of 0 and an informative note."""
    result = agent.evaluate_reply("")
    assert result["score"] == 0
    assert any("empty" in note.lower() for note in result["notes"])

    result_whitespace = agent.evaluate_reply("   ")
    assert result_whitespace["score"] == 0


# 2. Empathetic and actionable representative reply
def test_empathetic_and_actionable_reply(agent):
    """A reply expressing empathy and providing clear next steps earns full points."""
    reply = (
        "I am very sorry for the delay with your order. "
        "Let me check the courier tracking right away for you. "
        "Could you please confirm your delivery address?"
    )
    result = agent.evaluate_reply(reply)
    assert any("Empathy (15/15)" in n for n in result["notes"])
    assert any("Actionability (15/15)" in n for n in result["notes"])


# 3. Relevance using earlier customer messages in history
def test_relevance_using_earlier_customer_history(agent):
    """Relevance detects the customer's delivery issue from conversation history."""
    history = [
        {"role": "customer", "text": "My package tracking shows delayed in transit."},
        {"role": "agent", "text": "I will look into that for you."},
    ]
    reply = "I apologize for the delay. I will track your delivery status right away."
    result = agent.evaluate_reply(reply, customer_message=None, history=history)

    assert any("Relevance (15/15)" in n for n in result["notes"])


# 4. Relevance ignoring representative and system messages
def test_relevance_ignoring_representative_and_system_messages(agent):
    """Relevance is skipped when history contains only agent and system turns."""
    history = [
        {"role": "agent", "text": "Can you provide your tracking number?"},
        {"role": "system", "text": "Session initiated with support agent."},
    ]
    reply = "I apologize for the delay. I will track your delivery right away."
    result = agent.evaluate_reply(reply, customer_message=None, history=history)

    # Since no customer turns exist, Relevance should be safely skipped
    assert any("Relevance: Skipped" in n for n in result["notes"])


# 5. Relevance skipped when no customer context exists
def test_relevance_skipped_when_no_customer_context(agent):
    """Relevance is skipped and clearly noted when customer context is omitted."""
    reply = "I am sorry for the delay. I will check this for you immediately."
    result = agent.evaluate_reply(reply, customer_message=None, history=None)

    assert any("Relevance: Skipped" in n for n in result["notes"])


# 6. Accuracy skipped when no policy documents are available
def test_accuracy_skipped_when_no_policies(agent):
    """Accuracy is skipped and clearly noted when no policy documents are provided."""
    reply = "I understand your concern. Let me check that right away."
    result = agent.evaluate_reply(reply, policies=None)

    assert any("Accuracy: Skipped" in n for n in result["notes"])


# 7. Accuracy gives 15 when a specific policy detail is supported
def test_accuracy_gives_15_for_supported_policy_detail(agent):
    """Accuracy awards 15/15 when a verified policy detail (original receipt) is cited."""
    policies = [
        {
            "text": "Returns are accepted within 30 days with the original receipt.",
            "doc_name": "returns_and_refunds.pdf",
        }
    ]
    reply = "I can help with your return. Please make sure you have the original receipt."
    result = agent.evaluate_reply(reply, policies=policies)

    assert any("Accuracy (15/15)" in n and "original receipt" in n for n in result["notes"])


# 8. Accuracy gives 10 for a general response without a detected unsupported claim
def test_accuracy_gives_10_for_general_response(agent):
    """Accuracy awards 10/15 for a general response lacking specific verifiable policy details."""
    policies = [
        {
            "text": "Returns are accepted within 30 days with the original receipt.",
            "doc_name": "returns_and_refunds.pdf",
        }
    ]
    reply = "I understand your concern. Let me check our store return procedures for you."
    result = agent.evaluate_reply(reply, policies=policies)

    assert any("Accuracy (10/15)" in n for n in result["notes"])


# 9. Accuracy gives 0 for an unsupported timeframe or guarantee
def test_accuracy_gives_0_for_unsupported_claim(agent):
    """Accuracy awards 0/15 when an unsupported timeframe or guarantee is stated."""
    policies = [
        {
            "text": "Refunds are processed within 5-10 business days.",
            "doc_name": "returns_and_refunds.pdf",
        }
    ]
    # The representative claims 5 minutes, which contradicts policy
    reply = "I apologize for the delay. I guarantee you will get your refund in 5 minutes."
    result = agent.evaluate_reply(reply, policies=policies)

    assert any("Accuracy (0/15)" in n for n in result["notes"])


# 10. Proportional normalization when one or more dimensions are skipped
def test_proportional_normalization_when_dimensions_skipped(agent):
    """When context-dependent dimensions are skipped, the score is fairly normalized to 100."""
    # Only reply_text provided -> Relevance, Accuracy, and Personalization are skipped.
    # Evaluated: Empathy (15), Tone (10), Clarity (15), Actionability (15), Professionalism (5) = 60 possible.
    reply = (
        "I am very sorry for the trouble with this issue. "
        "Let me check your account right away and update you. "
        "Could you please confirm your email address?"
    )
    result = agent.evaluate_reply(reply)

    # Should achieve 100% on evaluated dimensions (60/60 -> 100/100)
    assert result["score"] == 100
    assert any("Relevance: Skipped" in n for n in result["notes"])
    assert any("Accuracy: Skipped" in n for n in result["notes"])
    assert any("Personalization: Skipped" in n for n in result["notes"])


# 11. run() evaluates a reply only when the representative role is explicitly provided
def test_run_evaluates_reply_only_when_role_is_agent(agent):
    """run() evaluates replies when role='agent', and suggests responses for customer turns."""
    session = Session(session_id="sess-test-01", product="Acme Store")

    # 1. When role is explicitly 'agent', it evaluates the reply
    res_agent = agent.run(
        session,
        "I am very sorry for the delay. Let me check your order details right away.",
        role="agent",
    )
    assert isinstance(res_agent, AgentResult)
    assert res_agent.result["action"] == "evaluate_reply"
    assert "score" in res_agent.result
    assert "notes" in res_agent.result

    # 2. When role is 'customer', it generates a suggested response
    res_customer = agent.run(session, "Where is my order?", role="customer")
    assert isinstance(res_customer, AgentResult)
    assert res_customer.result["action"] == "suggest_response"
    assert "suggestion" in res_customer.result

    # 3. When role is not specified (e.g. fresh orchestrator call), it defaults to suggesting response
    res_default = agent.run(session, "Where is my order?")
    assert res_default.result["action"] == "suggest_response"


# 12. suggest_response() still works
def test_suggest_response_works(agent):
    """suggest_response() returns a non-empty, polite suggestion."""
    session = Session(session_id="sess-test-02", product="Acme Online Store")
    suggestion = agent.suggest_response("Where is my delivery?", session=session)

    assert isinstance(suggestion, str)
    assert len(suggestion) > 20
    assert "Acme Online Store" in suggestion or "our store" in suggestion.lower()
