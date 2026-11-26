from backend.agents.coaching_agent import CoachingResponseAgent
from backend.agents.escalation_agent import EscalationRiskMonitorAgent
from backend.orchestrator.escalation_schemas import EscalationRiskRequest
from backend.services import rag_stub

_coaching_agent = CoachingResponseAgent()
_escalation_agent = EscalationRiskMonitorAgent()


NEG = [
    "angry", "ridiculous", "unacceptable", "worst", "terrible", "furious",
    "useless", "still", "again", "waiting", "never", "not working",
    "broken", "cancel", "lawyer", "complaint", "charged", "twice",
    "problem", "issue", "!!",
]
POS = [
    "thanks", "thank you", "great", "perfect", "appreciate", "resolved",
    "works", "happy", "helpful",
]
INTENTS = {
    "Refund / billing": ["refund", "charge", "billing", "invoice", "payment", "money"],
    "Cancellation": ["cancel", "close my account", "unsubscribe"],
    "Technical issue": ["error", "not working", "broken", "crash", "login", "bug", "app"],
    "Delivery / order": ["delivery", "order", "shipping", "package", "tracking"],
    "Account access": ["password", "account", "locked", "access"],
}

LADDERS = {
    "Calm": [
        "Hi, I need help with {p}. {s}",
        "Okay, I tried that but it's still the same. Could you check again?",
        "Alright, thanks. How long will this take?",
        "I see. Is there anything else I can try on my side?",
        "Great, that works now. Thank you!",
    ],
    "Impatient": [
        "Hello, {p} is giving me trouble. {s} I need this fixed fast.",
        "That's not helpful, I've already tried that. Can we move quicker?",
        "I'm still waiting for a real answer. This is taking too long!",
        "Honestly this is unacceptable. I need a solution right now.",
        "Fine. If it works, I'll be done with this.",
    ],
    "Angry": [
        "This is ridiculous! {s} {p} has been terrible!!",
        "I've contacted you again and nothing is fixed. This is the worst service!",
        "I want a refund and I'm ready to cancel. Get me a manager!",
        "You keep repeating yourselves. I'm furious and will file a complaint.",
        "Okay... fine. Just fix it and I may reconsider.",
    ],
    "Confused": [
        "Hi, I'm not sure what's happening with {p}. {s}",
        "Sorry, I don't understand what you mean. Where do I find that?",
        "I'm confused, can you explain step by step?",
        "Okay, I tried it but I'm not sure it worked. Did it?",
        "Oh I see now, thank you so much for explaining.",
    ],
}


def derive_recommendation_type(chunk: dict) -> str:
    """Derive recommendation type ('Article' | 'FAQ' | 'Troubleshooting') from chunk heading/content."""
    doc_name = (chunk.get("doc_name") or chunk.get("source") or "").lower()
    text = (chunk.get("text") or "").lower()

    if "faq" in doc_name or "?" in text or "how do i" in text or "can i" in text or "what is" in text:
        return "FAQ"

    troubleshoot_words = ("troubleshoot", "repair", "fix", "damaged", "faulty", "error", "steps", "replace", "issue")
    if any(k in doc_name for k in ("troubleshoot", "repair")) or any(k in text for k in troubleshoot_words):
        return "Troubleshooting"

    return "Article"


def simulate_customer(cfg, turn):
    """Return a simulated customer message for the selected persona and emotional progression."""
    progression = (cfg.get("emotional_progression") or "").lower()
    persona = cfg.get("customer_type") or cfg.get("persona", "Calm")

    if progression == "gets_angrier":
        if turn == 0:
            ladder_key = persona if persona in LADDERS else "Calm"
        elif turn == 1:
            ladder_key = "Impatient"
        else:
            ladder_key = "Angry"
    elif progression == "calms_down":
        if turn == 0:
            ladder_key = "Angry"
        elif turn == 1:
            ladder_key = "Impatient"
        else:
            ladder_key = "Calm"
    elif progression == "stays_calm":
        ladder_key = "Calm"
    else:
        ladder_key = persona if persona in LADDERS else "Calm"

    ladder = LADDERS.get(ladder_key, LADDERS["Calm"])
    message_index = min(turn, len(ladder) - 1)
    return ladder[message_index].format(
        p=cfg.get("product", "your product"),
        s=cfg.get("scenario", ""),
    )


def analyze_turn(text, history, cfg):
    """Analyze intent, sentiment, escalation risk, coaching, and knowledge."""
    t = text.lower()
    neg = sum(word in t for word in NEG)
    pos = sum(word in t for word in POS)
    n_cust = sum(
        1 for m in history
        if (m.get("role") if isinstance(m, dict) else getattr(m, "speaker", None)) == "customer"
    )

    urgency = 6 if any(word in t for word in ("today", "asap", "immediately", "urgent")) else 0
    billing_issue = 8 if any(word in t for word in ("charged", "refund", "billing", "invoice", "payment", "twice")) else 0
    frustration = max(
        0,
        min(
            100,
            20 + neg * 10 - pos * 20
            + billing_issue
            + urgency
            + (10 if t.count("!") >= 2 else 0)
            + n_cust * 4,
        ),
    )
    emotion = (
        "Angry" if frustration >= 75
        else "Frustrated" if frustration >= 50
        else "Satisfied" if frustration <= 20
        else "Neutral"
    )
    sentiment = {
        "Angry": "Negative",
        "Frustrated": "Negative",
        "Neutral": "Neutral",
        "Satisfied": "Positive",
    }[emotion]
    intent = next(
        (name for name, words in INTENTS.items() if any(word in t for word in words)),
        "General inquiry",
    )

    # Invoke EscalationRiskMonitorAgent for calibrated risk scoring & warning flags
    cfg_dict = cfg if isinstance(cfg, dict) else getattr(cfg, "__dict__", {})
    req = EscalationRiskRequest(
        message=text,
        history=history,
        frustration_score=frustration,
        turn_count=n_cust + 1,
        customer_type=cfg_dict.get("customer_type") or cfg_dict.get("persona"),
        product=cfg_dict.get("product"),
    )
    esc_response = _escalation_agent.analyze(req)

    chunks = rag_stub.retrieve(text, k=3)
    suggestion = _coaching_agent.suggest_response(
        customer_text=text,
        session=cfg_dict,
        history=history,
        intent=intent,
        emotion=emotion,
        escalation_response=esc_response,
        policy_chunks=chunks,
    )

    return {
        "intent": intent,
        "emotion": emotion,
        "sentiment": sentiment,
        "frustration": frustration,
        "risk": esc_response.risk_score,
        "risk_level": esc_response.risk_level.value,
        "risk_reason": "; ".join(esc_response.reasons) or "No strong escalation signals.",
        "strategy": esc_response.recommended_strategy,
        "warning_flags": esc_response.warning_flags,
        "flag_details": [f.model_dump() for f in esc_response.flag_details],
        "requires_supervisor": esc_response.requires_supervisor,
        "tier2_eligible": esc_response.tier2_eligible,
        "frustration_trend": esc_response.frustration_trend,
        "suggested_de_escalation_phrase": esc_response.suggested_de_escalation_phrase,
        "suggestion": suggestion,
        "chunks": chunks,
    }


def evaluate_agent_reply(
    text,
    customer_message=None,
    history=None,
    policies=None,
    product_name=None,
):
    """Evaluate an agent reply across 8 coaching dimensions using CoachingResponseAgent."""
    return _coaching_agent.evaluate_reply(
        reply_text=text,
        customer_message=customer_message,
        history=history,
        policies=policies,
        product_name=product_name,
    )


SAMPLE_TRANSCRIPT = """Customer: Hi, my refund for order #4521 still hasn't arrived after 10 days.
Agent: Hello! I'm sorry about the delay. Let me check the status for you.
Customer: This is the third time I'm contacting you. It's ridiculous!
Agent: I understand your frustration. I can see the refund was initiated on the 3rd and is pending at the bank.
Customer: I don't care about the bank. I want my money back or I'll cancel my account.
Agent: I'm escalating this now and will email you a confirmation within 24 hours.
Customer: Okay, thanks. Please make sure it actually happens this time.
"""
