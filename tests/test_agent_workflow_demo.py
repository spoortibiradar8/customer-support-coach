from frontend.views.agent_workflow_demo import _coerce_workflow_payload


def test_coerce_workflow_payload_uses_backend_analysis():
    payload = _coerce_workflow_payload("I was charged twice and need a refund")

    assert "customer_message" in payload
    assert payload["customer_message"] == "I was charged twice and need a refund"
    assert "intent" in payload
    assert "emotion" in payload
    assert "frustration_trend" in payload
    assert isinstance(payload.get("matched_kb", []), list)


def test_coerce_workflow_payload_reflects_positive_customer_message():
    payload = _coerce_workflow_payload("Thanks for fixing this, everything works perfectly now.")

    assert payload["emotion"] == "Satisfied"
    assert payload["frustration_trend"] == "stable"


def test_coerce_workflow_payload_reflects_billing_complaint():
    payload = _coerce_workflow_payload("I was charged twice and I need this fixed today.")

    assert payload["emotion"] == "Frustrated"
    assert payload["frustration_trend"] in {"rising", "elevated"}
