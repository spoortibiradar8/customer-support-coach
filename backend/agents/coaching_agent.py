"""Coaching & Response Suggestion Agent (Member 4).

Evaluates trainee support representative replies across 8 coaching dimensions
and generates policy-grounded suggested responses using the local ChromaDB RAG pipeline.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from backend.core.data_models import AgentResult, Session
from backend.services import rag_stub

logger = logging.getLogger(__name__)

# Domain keyword clusters for relevance matching (generic 'order' excluded to require specific topic indicators)
DOMAINS: dict[str, list[str]] = {
    "refund / billing": [
        "refund", "refunds", "charge", "charged", "billing", "invoice",
        "payment", "card", "fee", "cost", "money", "deducted", "double",
    ],
    "shipping / delivery": [
        "shipping", "ship", "delivery", "delivered", "parcel",
        "tracking", "courier", "dispatch", "late", "arrive", "transit",
        "carrier", "delayed", "lost package", "shipped",
    ],
    "account access": [
        "password", "account", "login", "locked", "signin", "sign-in",
        "email", "2fa", "two-step", "reset", "code", "credentials",
    ],
    "cancellation": [
        "cancel", "cancellation", "unsubscribe", "close account", "stop subscription",
    ],
    "returns / damaged": [
        "return", "returns", "exchange", "damaged", "broken", "faulty",
        "replacement", "warranty", "box", "package", "label",
    ],
}

# Common words ignored during generic keyword overlap checks
STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "i", "my", "me", "you",
    "your", "we", "our", "to", "for", "in", "on", "at", "by", "from",
    "and", "or", "so", "it", "this", "that", "do", "does", "did", "can",
    "could", "would", "should", "have", "has", "had", "please", "thanks", "thank",
    "order",  # Generic e-commerce term: does not indicate a specific problem domain
}


def _eval_empathy(lower_text: str) -> tuple[int, str]:
    """Dimension 1: Empathy (15 points)."""
    empathy_keywords = [
        "sorry", "apologize", "apologies", "understand",
        "frustrat", "inconvenience", "thank", "thanks", "appreciate",
        "glad", "happy to help", "my pleasure",
    ]
    if any(keyword in lower_text for keyword in empathy_keywords):
        return 15, "✅ Empathy (15/15): Acknowledged customer feelings and expressed courtesy."
    return 0, "⚠️ Empathy (0/15): Missing validation or apology. Consider saying 'I understand your frustration' or 'I apologize for the trouble'."


def _eval_tone(text: str, lower_text: str) -> tuple[int, str]:
    """Dimension 2: Tone (10 points)."""
    defensive_phrases = [
        "not our fault", "not our problem", "you should have",
        "you failed to", "as i already said", "policy says no",
        "read the terms", "you must wait", "calm down",
    ]
    found_defensive = [phrase for phrase in defensive_phrases if phrase in lower_text]
    words = text.split()
    is_shouting = (len(words) >= 3 and text.isupper()) or text.count("!") > 2

    if found_defensive:
        return 0, f"⚠️ Tone (0/10): Defensive language detected ('{found_defensive[0]}'). Aim for a supportive tone."
    if is_shouting:
        return 3, "⚠️ Tone (3/10): Avoid ALL CAPS and excessive exclamation marks ('!')."
    return 10, "✅ Tone (10/10): Calm, warm, and respectful phrasing."


def _eval_clarity(word_count: int) -> tuple[int, str]:
    """Dimension 3: Clarity (15 points)."""
    if 12 <= word_count <= 70:
        return 15, f"✅ Clarity (15/15): Well-paced, clear length ({word_count} words)."
    if 8 <= word_count < 12:
        return 10, f"⚠️ Clarity (10/15): Slightly brief ({word_count} words). Ensure the explanation is fully detailed."
    if 71 <= word_count <= 95:
        return 10, f"⚠️ Clarity (10/15): Slightly long ({word_count} words). Aim to keep turns concise."
    if word_count < 8:
        return 4, f"⚠️ Clarity (4/15): Too brief ({word_count} words) for a helpful support explanation."
    return 5, f"⚠️ Clarity (5/15): Overly long ({word_count} words). Break long explanations into shorter turns."


def _eval_relevance(
    lower_reply: str,
    customer_message: str | None,
    history: list[dict[str, Any]] | None = None,
) -> tuple[int, str] | None:
    """Dimension 4: Relevance (15 points).
    
    Compares the reply against the customer's message and customer turns in history.
    Strictly ignores agent and system turns.
    """
    customer_texts: list[str] = []
    if customer_message and customer_message.strip():
        customer_texts.append(customer_message.strip().lower())

    # Include prior turns from customer/user only
    if history:
        for item in history:
            speaker = ""
            content = ""
            if isinstance(item, dict):
                speaker = (item.get("role") or item.get("speaker") or "").lower()
                content = item.get("text") or item.get("content") or ""
            elif hasattr(item, "speaker"):
                sp = getattr(item, "speaker", "")
                speaker = getattr(sp, "value", str(sp)).lower()
                content = getattr(item, "content", "") or getattr(item, "text", "")

            if speaker in ("customer", "user") and content.strip():
                customer_texts.append(content.strip().lower())

    if not customer_texts:
        return None  # Skipped: cannot evaluate without customer messages

    cust_full_text = " ".join(customer_texts)

    # Domain-level matching
    cust_domains = [d for d, kws in DOMAINS.items() if any(k in cust_full_text for k in kws)]
    if cust_domains:
        matched_domains = [d for d in cust_domains if any(k in lower_reply for k in DOMAINS[d])]
        if matched_domains:
            return 15, f"✅ Relevance (15/15): Directly addresses customer's {matched_domains[0]} issue."
        return 0, f"⚠️ Relevance (0/15): Customer asked about {cust_domains[0]}, but your reply does not address it."

    # Salient non-stopword overlap (excluding generic 'order')
    cust_tokens = set(re.findall(r"\b[a-z]{3,}\b", cust_full_text)) - STOP_WORDS
    reply_tokens = set(re.findall(r"\b[a-z]{3,}\b", lower_reply)) - STOP_WORDS
    overlap = cust_tokens & reply_tokens

    if len(overlap) >= 2:
        return 15, "✅ Relevance (15/15): Directly on-topic with the customer's specific inquiry."
    if len(overlap) == 1:
        return 8, "⚠️ Relevance (8/15): Partially on-topic; make sure to address the core problem directly."
    return 0, "⚠️ Relevance (0/15): Reply does not seem to address what the customer asked."


def _eval_accuracy(lower_reply: str, policies: list[dict[str, Any]] | None) -> tuple[int, str] | None:
    """Dimension 5: Accuracy & Knowledge Alignment (15 points).
    
    A keyword-based evaluator to check for verifiable claims and detect unsupported timeframes/guarantees.
    """
    if not policies:
        return None  # Skipped: no policy documents provided for this turn

    policy_corpus = " ".join((p.get("text") or "") for p in policies).lower()
    if not policy_corpus.strip():
        return None  # Skipped: policy text is empty

    # 1. Check for stated timeframes (e.g. '10 days', '24 hours', '3 business days')
    timeframe_matches = re.findall(
        r"\b(\d+\s*(?:business\s*)?(?:days?|hours?|weeks?|mins?|minutes?))\b",
        lower_reply,
    )

    # 2. Check for strong guarantee terms
    guarantee_terms = ["guarantee", "guaranteed", "promise", "free replacement immediately"]
    found_guarantees = [g for g in guarantee_terms if g in lower_reply]

    # Stated timeframe checks
    if timeframe_matches:
        unsupported_tf = [tf for tf in timeframe_matches if tf not in policy_corpus]
        if unsupported_tf:
            return 0, f"⚠️ Accuracy (0/15): Stated timeframe ('{unsupported_tf[0]}') is not found in retrieved policy guidelines."
        return 15, f"✅ Accuracy (15/15): Stated timeframe ('{timeframe_matches[0]}') is verified by official policy."

    # Guarantee checks
    if found_guarantees:
        unsupported_g = [g for g in found_guarantees if g not in policy_corpus]
        if unsupported_g:
            return 0, f"⚠️ Accuracy (0/15): Unverified commitment ('{unsupported_g[0]}') is not supported by policy guidelines."
        return 15, f"✅ Accuracy (15/15): Specific commitment ('{found_guarantees[0]}') is verified by official policy."

    # 3. Check for specific policy rule details (procedural phrases)
    SPECIFIC_POLICY_RULES = [
        "original receipt", "original packaging", "prepaid label", "return label",
        "store credit", "bank transfer", "proof of purchase", "restocking fee",
        "rma", "serial number", "carrier tracking", "standard delivery", "express delivery",
    ]
    verified_rules = [rule for rule in SPECIFIC_POLICY_RULES if rule in lower_reply and rule in policy_corpus]
    if verified_rules:
        return 15, f"✅ Accuracy (15/15): Specific policy rule ('{verified_rules[0]}') verified against retrieved documentation."

    # 4. General response with no detected unsupported claims, but lacking specific verifiable detail
    return 10, "ℹ️ Accuracy (10/15): General response with no detected unsupported claims; contains insufficient detail for full verification."


def _eval_actionability(lower_text: str, text: str) -> tuple[int, str]:
    """Dimension 6: Actionability & Ownership (15 points)."""
    ownership_phrases = [
        "i will", "let me", "i have", "we will", "i am escalating",
        "i'm checking", "i am looking", "let's", "i can check",
    ]
    action_steps = [
        "check", "track", "refund", "update", "verify", "status",
        "cancel", "submit", "please provide", "could you", "can you",
        "confirm", "share",
    ]

    has_ownership = any(phrase in lower_text for phrase in ownership_phrases)
    has_action = any(term in lower_text for term in action_steps) or "?" in text

    if has_ownership and has_action:
        return 15, "✅ Actionability (15/15): Took personal ownership and gave a clear next step or question."
    if has_ownership or has_action:
        return 10, "⚠️ Actionability (10/15): Has ownership or action step, but combine both for best results (e.g. 'I will check this right away. Could you confirm your order ID?')."
    return 0, "⚠️ Actionability (0/15): Passive response. State clearly what you will do next or ask a guiding question."


def _eval_personalization(
    lower_reply: str,
    customer_message: str | None,
    history: list[dict[str, Any]] | None,
    product_name: str | None,
) -> tuple[int, str] | None:
    """Dimension 7: Personalization & Context Awareness (10 points).
    
    Inspects customer messages from customer_message and history.
    Strictly ignores agent and system messages to avoid false context.
    """
    customer_texts: list[str] = []
    if customer_message and customer_message.strip():
        customer_texts.append(customer_message.strip())

    # Collect past turns belonging ONLY to the customer/user
    if history:
        for item in history:
            speaker = ""
            content = ""
            if isinstance(item, dict):
                speaker = (item.get("role") or item.get("speaker") or "").lower()
                content = item.get("text") or item.get("content") or ""
            elif hasattr(item, "speaker"):
                sp = getattr(item, "speaker", "")
                speaker = getattr(sp, "value", str(sp)).lower()
                content = getattr(item, "content", "") or getattr(item, "text", "")

            # Filter strictly for customer turns
            if speaker in ("customer", "user") and content.strip():
                customer_texts.append(content.strip())

    if not customer_texts:
        return None  # Skipped: no customer messages found

    combined_cust_text = " ".join(customer_texts)

    # Check for order identifier in customer turns (e.g. #1234 or numbers >= 4 digits)
    cust_order_ids = re.findall(r"#\d+|\b\d{4,}\b", combined_cust_text)
    cust_product = (product_name or "").lower().strip()

    used_order_id = any(oid.lower() in lower_reply for oid in cust_order_ids)
    used_product = bool(cust_product and cust_product != "our store" and cust_product in lower_reply)

    if cust_order_ids and used_order_id:
        return 10, f"✅ Personalization (10/10): Referenced customer's specific order identifier ({cust_order_ids[0]})."
    if used_product:
        return 10, f"✅ Personalization (10/10): Specifically referenced the product ({product_name})."

    # If customer supplied an order ID in the conversation, but representative ignored it:
    if cust_order_ids and not used_order_id:
        return 3, f"⚠️ Personalization (3/10): Customer mentioned order {cust_order_ids[0]} in the conversation. Acknowledge their specific order number."

    # If customer never gave an order ID, check if agent asked for relevant details to personalize:
    has_detail_ask = any(
        phrase in lower_reply
        for phrase in [
            "order number", "order id", "order details", "tracking number",
            "account details", "receipt", "email address", "your order",
        ]
    )
    if has_detail_ask:
        return 10, "✅ Personalization (10/10): Appropriately asked for customer details to personalize the interaction."

    return 5, "⚠️ Personalization (5/10): Response is somewhat generic. Reference the customer's specific issue or ask for their details."


def _eval_professionalism(text: str, lower_text: str) -> tuple[int, str]:
    """Dimension 8: Professionalism (5 points)."""
    slang_words = ["idk", "gonna", "wanna", "dunno", "nope", "yeah", "kinda", "ya", "u"]
    found_slang = [s for s in slang_words if re.search(rf"\b{s}\b", lower_text)]
    repeated_punct = bool(re.search(r"\?{2,}|\!{2,}", text))

    if found_slang:
        return 0, f"⚠️ Professionalism (0/5): Avoid informal slang ('{found_slang[0]}') in customer support."
    if repeated_punct:
        return 2, "⚠️ Professionalism (2/5): Avoid repeated punctuation ('??', '!!')."
    return 5, "✅ Professionalism (5/5): Professional phrasing, calm formatting, and zero slang."


class CoachingResponseAgent:
    """Coaching & Response Suggestion Agent for customer support trainees."""

    AGENT_TYPE = "coaching-response-agent"

    def __init__(self, min_policy_score: float = 0.20) -> None:
        self.min_policy_score = min_policy_score

    def evaluate_reply(
        self,
        reply_text: str,
        customer_message: str | None = None,
        history: list[dict[str, Any]] | None = None,
        policies: list[dict[str, Any]] | None = None,
        product_name: str | None = None,
    ) -> dict[str, Any]:
        """Evaluate a support representative's reply across 8 coaching dimensions.
        
        Supports proportional normalization: if customer_message or policies
        are not provided, those dimensions are excluded from the denominator so
        the score remains fair.
        
        Returns a dictionary with:
          - score: integer from 0 to 100
          - notes: list of constructive feedback strings
        """
        text = (reply_text or "").strip()
        if not text:
            return {
                "score": 0,
                "notes": ["⚠️ The reply is empty. Please provide a helpful response."],
            }

        words = text.split()
        word_count = len(words)
        lower_text = text.lower()

        total_earned = 0
        total_possible = 0
        notes: list[str] = []

        # 1. Empathy (15 points)
        earned, note = _eval_empathy(lower_text)
        total_earned += earned
        total_possible += 15
        notes.append(note)

        # 2. Tone (10 points)
        earned, note = _eval_tone(text, lower_text)
        total_earned += earned
        total_possible += 10
        notes.append(note)

        # 3. Clarity (15 points)
        earned, note = _eval_clarity(word_count)
        total_earned += earned
        total_possible += 15
        notes.append(note)

        # 4. Relevance (15 points)
        res_relevance = _eval_relevance(lower_text, customer_message, history)
        if res_relevance is not None:
            earned, note = res_relevance
            total_earned += earned
            total_possible += 15
            notes.append(note)
        else:
            notes.append("ℹ️ Relevance: Skipped (no customer message provided to compare).")

        # 5. Accuracy & Knowledge Alignment (15 points)
        res_accuracy = _eval_accuracy(lower_text, policies)
        if res_accuracy is not None:
            earned, note = res_accuracy
            total_earned += earned
            total_possible += 15
            notes.append(note)
        else:
            notes.append("ℹ️ Accuracy: Skipped (no retrieved policy documents provided for verification).")

        # 6. Actionability & Ownership (15 points)
        earned, note = _eval_actionability(lower_text, text)
        total_earned += earned
        total_possible += 15
        notes.append(note)

        # 7. Personalization & Context (10 points)
        res_personal = _eval_personalization(lower_text, customer_message, history, product_name)
        if res_personal is not None:
            earned, note = res_personal
            total_earned += earned
            total_possible += 10
            notes.append(note)
        else:
            notes.append("ℹ️ Personalization: Skipped (no customer message or context provided to compare).")

        # 8. Professionalism (5 points)
        earned, note = _eval_professionalism(text, lower_text)
        total_earned += earned
        total_possible += 5
        notes.append(note)

        # Proportional Normalization
        if total_possible > 0:
            final_score = int(round((total_earned / total_possible) * 100))
            final_score = max(0, min(100, final_score))
        else:
            final_score = 0

        return {
            "score": final_score,
            "notes": notes,
        }

    def suggest_response(self, customer_text: str, session: Any = None) -> str:
        """Generate a polite, helpful response grounded in retrieved policy documentation.
        
        Uses rag_stub.retrieve() to search the knowledge base. If policy information
        is found above the score threshold, it grounds the answer in that policy.
        If no relevant policy is found, it does not invent fake rules.
        """
        query = (customer_text or "").strip()
        if not query:
            return "Hello! How may I assist you with your inquiry today?"

        product_name = "our store"
        if session:
            product_name = getattr(session, "product", None) or "our store"

        # Retrieve relevant policy chunks from ChromaDB
        retrieved_chunks: list[dict[str, Any]] = []
        try:
            retrieved_chunks = rag_stub.retrieve(query=query, k=2)
        except Exception as exc:
            logger.warning("RAG retrieval failed during response suggestion: %s", exc)

        # Filter out chunks that fell below the relevance score threshold
        valid_chunks = [
            chunk for chunk in retrieved_chunks
            if chunk.get("score", 0.0) >= self.min_policy_score
        ]

        # Case 1: Policy information was found
        if valid_chunks:
            top_hit = valid_chunks[0]
            doc_name = top_hit.get("doc_name") or top_hit.get("source", "our documentation")
            doc_text = top_hit.get("text", "").strip()

            # Extract the first sentence of the retrieved policy chunk
            policy_excerpt = doc_text.split(".")[0].strip()
            if len(policy_excerpt) > 120:
                policy_excerpt = policy_excerpt[:120].rstrip() + "..."

            return (
                f"Thank you for contacting us regarding {product_name}. "
                f"Under our {doc_name} policy ({policy_excerpt}.), I will be happy to assist you. "
                "Could you please share your order or account details so I can take care of this for you?"
            )

        # Case 2: No policy match found — do NOT invent policy rules
        return (
            f"Thank you for reaching out regarding {product_name}. "
            "I understand your request and would be glad to help resolve this for you. "
            "Could you please provide a few more details so I can look into this right away?"
        )

    def run(self, session: Any, message: str, role: str | None = None) -> AgentResult:
        """Standard orchestrator agent entry point: agent.run(session, message) -> AgentResult.
        
        Uses the explicitly provided role to select the operation:
          - role='agent' -> evaluate_reply(message)
          - role='customer' (or missing/unrecognized) -> suggest_response(message, session)
        """
        clean_message = (message or "").strip()
        session_id = getattr(session, "session_id", "sess-default") or "sess-default"

        # Normalize role string
        normalized_role = str(role).lower().strip() if role else None

        # 1. Representative reply: evaluate the response
        if normalized_role in ("agent", "representative", "reply"):
            customer_msg = None
            history = None
            product = None

            # Retrieve history and product safely for both dict and Session object
            if isinstance(session, dict):
                history = session.get("messages", [])
                product = session.get("product")
            elif session:
                history = getattr(session, "messages", None)
                product = getattr(session, "product", None)

            # First, try to retrieve the latest ACTUAL customer message from history
            if history:
                for item in reversed(history):
                    speaker = ""
                    text = ""
                    if isinstance(item, dict):
                        speaker = (item.get("role") or item.get("speaker") or "").lower()
                        text = item.get("text") or item.get("content") or ""
                    elif hasattr(item, "speaker"):
                        sp = getattr(item, "speaker", "")
                        speaker = getattr(sp, "value", str(sp)).lower()
                        text = getattr(item, "content", "") or getattr(item, "text", "")

                    if speaker in ("customer", "user") and text.strip():
                        customer_msg = text.strip()
                        break

            # If no actual customer message is found in history, customer_msg remains None.
            # We do NOT fall back to session.scenario, so context-dependent dimensions can be skipped fairly.

            # Retrieve policy chunks only if an actual customer query is available
            policies = None
            if customer_msg:
                try:
                    policies = rag_stub.retrieve(query=customer_msg, k=2)
                except Exception:
                    policies = None

            evaluation = self.evaluate_reply(
                clean_message,
                customer_message=customer_msg,
                history=history,
                policies=policies,
                product_name=product,
            )
            payload = {
                "action": "evaluate_reply",
                "score": evaluation["score"],
                "notes": evaluation["notes"],
                "evaluation": evaluation,
            }
        # 2. Customer message (or missing/unrecognized): suggest a response
        else:
            suggestion = self.suggest_response(clean_message, session)
            payload = {
                "action": "suggest_response",
                "suggestion": suggestion,
                "suggested_response": suggestion,
            }

        return AgentResult(
            session_id=session_id,
            agent_type=self.AGENT_TYPE,
            result=payload,
        )
