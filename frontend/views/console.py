
"""Three-panel live coaching console."""

import re
import streamlit as st

from backend.services import pipeline_stub as pipe
from backend.services import storage
from backend.services.validation import validate_message
from backend.agents.knowledge_agent import KnowledgeRecommendationAgent
from backend.agents.escalation_agent import EscalationRiskMonitorAgent

RISK_ALERT = 70

knowledge_agent = KnowledgeRecommendationAgent()
escalation_agent = EscalationRiskMonitorAgent()


def get_console_data(sid):
    key = f"console_data_{sid}"

    if key not in st.session_state:
        session = storage.load(sid) or {}

        st.session_state[key] = {
            "messages": session.get("messages", []),
            "analyses": session.get("analyses", []),
            "tone": session.get("tone", []),
            "replay_idx": session.get("replay_idx", 0),
        }

    return st.session_state[key]


def save_console_data(data, config):
    session = storage.load(config["session_id"]) or {}

    session.update({
        "session_id": config["session_id"],
        "mode": config["mode"],
        "product": config["product"],
        "scenario": config["scenario"],
        "persona": config["persona"],
        "max_turns": config["max_turns"],
        "replay_transcript": config["replay_transcript"],
        "messages": data["messages"],
        "analyses": data["analyses"],
        "tone": data["tone"],
        "replay_idx": data["replay_idx"],
    })

    storage.save(session)


def generate_knowledge_response(message, passages):
    if not passages:
        return None

    query = message.lower()
    combined = " ".join(
        passage.get("text", "")
        for passage in passages
    )

    def normalize(text):
        text = text.lower()
        text = text.replace("’", "'").replace("‘", "'")
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return " ".join(text.split())

    content = normalize(combined)
    normalized_query = normalize(query)

    account_access = any(
        phrase in normalized_query
        for phrase in [
            "password",
            "reset",
            "login",
            "log in",
            "account access",
            "unable to access",
            "cannot access",
            "can't access",
        ]
    )

    if account_access:
        instructions = [
            (
                "Open the sign-in page and select 'Forgot password'.",
                "open the sign in page",
                [
                    "already selected forgot password",
                    "already tried forgot password",
                    "already clicked forgot password",
                ],
            ),
            (
                "Enter the email address on your account.",
                "enter the email address",
                [
                    "verified my registered email",
                    "verified my email",
                    "confirmed my email address",
                    "already entered my email",
                ],
            ),
            (
                "We send a reset link that stays valid for 30 minutes.",
                "reset link",
                [
                    "received the reset link",
                    "received a password reset email",
                    "got the reset email",
                ],
            ),
            (
                "If no email arrives, check the spam folder and confirm that the address is spelled correctly.",
                "check the spam folder",
                [
                    "checked my spam folder",
                    "checked the spam folder",
                    "checked spam folder",
                    "already checked spam",
                ],
            ),
        ]

        selected = []

        for instruction, keyword, completed_phrases in instructions:
            if keyword not in content:
                continue

            already_done = any(
                phrase in normalized_query
                for phrase in completed_phrases
            )

            if not already_done:
                selected.append(instruction)

        locked_out = any(
            phrase in normalized_query
            for phrase in [
                "account locked",
                "account is locked",
                "locked out",
                "my account has been locked",
                "unable to sign in because my account is locked",
            ]
        )

        if locked_out and "after five failed sign in attempts" in content:
            selected.append(
                "After five failed sign-in attempts, the account is locked for 15 minutes."
            )

        return " ".join(selected) if selected else None

    stop_words = {
        "i", "me", "my", "the", "a", "an", "is", "am",
        "are", "to", "for", "of", "and", "or", "in",
        "on", "it", "this", "that", "can", "could",
        "please", "help", "you", "your", "with",
        "how", "what", "why", "do", "does", "unable",
        "we", "have", "has", "been", "but", "still",
        "did", "not", "i'm", "i've", "after", "again",
    }

    query_words = {
        word.lower()
        for word in re.findall(r"\b[a-zA-Z]+\b", message)
        if word.lower() not in stop_words
    }

    selected = []
    seen = set()

    for passage in passages:
        text = passage.get("text", "")
        sentences = re.split(r"(?<=[.!?])\s+|\n+", text)

        for sentence in sentences:
            sentence = sentence.strip()

            if len(sentence) < 20:
                continue

            if not re.search(r"[.!?]$", sentence):
                continue

            lower_sentence = sentence.lower()

            if any(
                heading in lower_sentence
                for heading in [
                    "acme gadgets",
                    "how do i",
                    "why is my",
                    "return window",
                    "how refunds",
                    "shipping and delivery",
                ]
            ):
                continue

            if sentence.isupper():
                continue

            words = {
                word.lower()
                for word in re.findall(r"\b[a-zA-Z]+\b", sentence)
            }

            if query_words.intersection(words):
                if lower_sentence not in seen:
                    selected.append(sentence)
                    seen.add(lower_sentence)

            if len(selected) >= 4:
                break

        if len(selected) >= 4:
            break

    return " ".join(selected) if selected else None


def customer_count(data):
    return sum(
        m["role"] == "customer"
        for m in data["messages"]
    )


def add_message(data, role, text, config):
    data["messages"].append({
        "role": role,
        "text": text,
    })

    if role == "customer":
        from backend.orchestrator.orchestrator import PipelineAnalysisAdapter

        adapter = PipelineAnalysisAdapter(
            history=data["messages"][:-1],
            config=config,
        )

        analysis = adapter.analyze(
            session=None,
            message=text,
        )

        try:
            escalation_result = escalation_agent.monitor(
                message=text,
                history=data["messages"][:-1],
                session_id=config["session_id"],
                frustration_score=analysis.get("frustration"),
                turn_count=customer_count(data),
                customer_type=config.get("persona"),
                product=config.get("product"),
            )

            status_value = getattr(
                escalation_result,
                "status",
                "error",
            )

            status = getattr(
                status_value,
                "value",
                status_value,
            )

            if status == "success":
                analysis["risk"] = escalation_result.risk_score

                analysis["risk_reason"] = "; ".join(
                    escalation_result.reasons
                )

                analysis["strategy"] = (
                    escalation_result.recommended_strategy
                )

                analysis["risk_level"] = getattr(
                    escalation_result.risk_level,
                    "value",
                    escalation_result.risk_level,
                )

                analysis["warning_flags"] = (
                    escalation_result.warning_flags
                )

                analysis["frustration_trend"] = (
                    escalation_result.frustration_trend
                )

                analysis["requires_supervisor"] = (
                    escalation_result.requires_supervisor
                )

                analysis["tier2_eligible"] = (
                    escalation_result.tier2_eligible
                )

                analysis["de_escalation_phrase"] = (
                    escalation_result.suggested_de_escalation_phrase
                )

                analysis["escalation_agent_status"] = "success"

            else:
                analysis["escalation_agent_status"] = "error"

                analysis["escalation_agent_error"] = (
                    getattr(
                        escalation_result,
                        "error",
                        None,
                    ) or "Agent execution failed."
                )

        except Exception as e:
            analysis["escalation_agent_status"] = "error"
            analysis["escalation_agent_error"] = str(e)

        knowledge_result = knowledge_agent.run(
            session={
                "session_id": config["session_id"],
                "product": config["product"],
                "messages": data["messages"],
            },
            message=text,
        )

        knowledge_data = knowledge_result.result or {}
        passages = knowledge_data.get("passages", [])

        analysis["chunks"] = passages

        analysis["knowledge_suggestion"] = generate_knowledge_response(
            text,
            passages,
        )

        data["analyses"].append(analysis)

    elif role == "agent":
        customer_messages = [
            m["text"] for m in data["messages"]
            if m["role"] == "customer"
        ]

        last_customer = (
            customer_messages[-1]
            if customer_messages else None
        )

        chunks = (
            data["analyses"][-1]["chunks"]
            if data["analyses"] else []
        )

        result = pipe.evaluate_agent_reply(
            text,
            customer_message=last_customer,
            history=data["messages"],
            policies=chunks,
            product_name=config["product"],
        )

        data["tone"].append(result)

    save_console_data(data, config)


def reply_form(data, config):
    with st.form(
        f"reply_{config['session_id']}_{len(data['messages'])}",
        clear_on_submit=True,
    ):
        reply = st.text_area(
            "Your reply to the customer",
            height=90,
        )

        submitted = st.form_submit_button(
            "Send reply",
            use_container_width=True,
        )

        if submitted:
            error = validate_message(reply, "Reply")

            if error:
                st.error(error)
            else:
                add_message(
                    data,
                    "agent",
                    reply.strip(),
                    config,
                )

                st.rerun()


def conversation_panel(data, config):
    st.markdown(
        '<p class="section-heading">Conversation</p>',
        unsafe_allow_html=True,
    )

    with st.container(height=380, border=True):
        if not data["messages"]:
            st.caption("No messages yet.")

        for message in data["messages"]:
            role = (
                "user" if message["role"] == "customer"
                else "assistant"
            )

            with st.chat_message(role):
                st.write(message["text"])

    mode = config["mode"]

    if mode == "Simulator":
        if customer_count(data) == 0:
            if st.button(
                "Start simulation",
                type="primary",
                use_container_width=True,
            ):
                message = pipe.simulate_customer(config, 0)
                add_message(data, "customer", message, config)
                st.rerun()

        else:
            reply_form(data, config)

            if st.button("Next simulated customer message"):
                count = customer_count(data)

                if count < config["max_turns"]:
                    message = pipe.simulate_customer(config, count)
                    add_message(data, "customer", message, config)
                    st.rerun()
                else:
                    st.success("Simulation completed.")

    elif mode == "Manual":
        with st.form(
            f"customer_{config['session_id']}",
            clear_on_submit=True,
        ):
            message = st.text_area(
                "Paste incoming customer message",
                height=90,
            )

            submitted = st.form_submit_button(
                "Add message and coach",
                use_container_width=True,
            )

            if submitted:
                error = validate_message(
                    message,
                    "Customer message",
                )

                if error:
                    st.error(error)
                else:
                    add_message(
                        data,
                        "customer",
                        message.strip(),
                        config,
                    )

                    st.rerun()

        if (
            data["messages"]
            and data["messages"][-1]["role"] == "customer"
        ):
            reply_form(data, config)

    else:
        script = config.get("replay_transcript") or []
        index = data["replay_idx"]
        total = len(script)

        st.progress(
            index / total if total else 0,
            text=f"Message {index} of {total}",
        )

        col_next, col_restart = st.columns(2)

        if col_next.button(
            "Next message",
            disabled=index >= total,
            type="primary",
            use_container_width=True,
        ):
            message = script[index]
            role = message.get("role", "customer")
            text = message.get("text", "")

            add_message(data, role, text, config)
            data["replay_idx"] += 1
            save_console_data(data, config)
            st.rerun()

        if col_restart.button(
            "Restart replay",
            use_container_width=True,
        ):
            data["messages"] = []
            data["analyses"] = []
            data["tone"] = []
            data["replay_idx"] = 0

            save_console_data(data, config)
            st.rerun()

        if index >= total:
            st.success("Replay completed.")


def coaching_panel(data):
    st.markdown(
        '<p class="section-heading">Coaching Feed</p>',
        unsafe_allow_html=True,
    )

    if not data["analyses"]:
        st.info("Waiting for the first customer message...")
        return

    analysis = data["analyses"][-1]
    status = analysis.get("escalation_agent_status")

    if status == "success":
        st.success("Escalation Risk Monitor: Active")

    elif status == "error":
        st.error(
            "Escalation Risk Monitor: Error — "
            + str(analysis.get("escalation_agent_error", "Unknown error"))
        )

    else:
        st.warning("Escalation Risk Monitor: Not available for this turn")

    col1, col2 = st.columns(2)

    col1.metric(
        "Sentiment",
        analysis["sentiment"],
        analysis["emotion"],
        delta_color="off",
    )

    col2.metric("Intent", analysis["intent"])

    st.caption(f"Frustration — {analysis['frustration']}%")
    st.progress(analysis["frustration"] / 100)

    st.caption(f"Escalation risk — {analysis['risk']}%")
    st.progress(analysis["risk"] / 100)

    if status == "success":
        st.caption(
            f"Risk level: {str(analysis['risk_level']).upper()}"
        )

        st.caption(
            f"Frustration trend: "
            f"{str(analysis['frustration_trend']).capitalize()}"
        )

        if analysis.get("warning_flags"):
            st.write(
                "**Warning flags:** "
                + ", ".join(analysis["warning_flags"])
            )

        if analysis.get("requires_supervisor"):
            st.warning("Supervisor handover recommended.")
        else:
            st.info("Supervisor handover not currently required.")

        if analysis.get("tier2_eligible"):
            st.warning("Eligible for Tier-2 escalation.")

    st.write(f"**Why:** {analysis['risk_reason']}")

    if analysis["risk"] >= RISK_ALERT:
        st.warning(
            f"**Recommended strategy:** {analysis['strategy']}"
        )

    with st.container(border=True):
        st.markdown("**Suggested response**")

        escalation_phrase = analysis.get("de_escalation_phrase")
        knowledge_suggestion = analysis.get("knowledge_suggestion")
        emotion = analysis.get("emotion", "Neutral")

        response_openers = {
            "Angry": (
                "I sincerely apologize for the frustration "
                "you have experienced. I'll take ownership "
                "of helping resolve this."
            ),
            "Frustrated": (
                "I'm sorry you're experiencing this issue. "
                "Let's work through this together."
            ),
            "Neutral": (
                "Thanks for sharing those details. "
                "I'll help you with this."
            ),
            "Satisfied": (
                "I'm glad to hear things are working well!"
            ),
        }

        response_opener = response_openers.get(
            emotion,
            response_openers["Neutral"],
        )

        if analysis.get("requires_supervisor") and escalation_phrase:
            suggested_response = escalation_phrase

            if knowledge_suggestion:
                suggested_response += (
                    "\n\nIn parallel, please try these steps: "
                    + knowledge_suggestion
                )

        elif knowledge_suggestion:
            suggested_response = (
                response_opener
                + "\n\n"
                + knowledge_suggestion
            )

        elif escalation_phrase:
            suggested_response = escalation_phrase

        else:
            suggested_response = analysis["suggestion"]

        st.markdown(suggested_response)

    if data["tone"]:
        latest = data["tone"][-1]

        with st.container(border=True):
            st.markdown(
                f"**Your last reply — score: {latest['score']}/100**"
            )

            for note in latest["notes"]:
                st.write(note)


def knowledge_panel(data):
    st.markdown(
        '<p class="section-heading">Knowledge</p>',
        unsafe_allow_html=True,
    )

    if not data["analyses"]:
        st.caption(
            "Relevant articles appear after a customer message."
        )
        return

    chunks = data["analyses"][-1]["chunks"]

    if not chunks:
        st.info("No relevant knowledge chunks found.")
        return

    for index, chunk in enumerate(chunks, 1):
        with st.container(border=True):
            source = chunk.get(
                "source",
                chunk.get("doc_name", "Document"),
            )

            page = chunk.get("page") or "N/A"
            score = chunk.get("score")
            score = score if score is not None else 0

            st.markdown(
                f"**#{index} — {source}** — Page {page}"
            )

            st.caption(
                f"Relevance score: {score}"
            )

            preview = chunk.get("text", "")
            st.write(preview[:350])


def render():
    st.markdown(
        "<h1>Live Coaching Console</h1>",
        unsafe_allow_html=True,
    )

    all_sessions = storage.list_sessions()

    if not all_sessions:
        st.info(
            "No sessions available. Create a session from Dashboard."
        )
        return

    session_ids = [
        item[0] for item in all_sessions
    ]

    selected = st.selectbox(
        "Select session",
        options=session_ids,
    )

    session = storage.load(selected)

    if not session:
        st.error("Could not load this session.")
        return

    config = {
        "session_id": selected,
        "mode": session["mode"],
        "product": session["product"],
        "scenario": session["scenario"] or "",
        "persona": session["persona"] or "Calm",
        "max_turns": session["max_turns"] or 5,
        "replay_transcript": session["replay_transcript"] or [],
    }

    st.caption(
        f"Mode: **{config['mode']}** | "
        f"Product: **{config['product']}** | "
        f"Session: `{selected}`"
    )

    data = get_console_data(selected)

    if data["analyses"]:
        latest = data["analyses"][-1]

        if latest["risk"] >= RISK_ALERT:
            st.error(
                f"HIGH ESCALATION RISK ({latest['risk']}%) — "
                f"{latest['risk_reason']}"
            )

    left, middle, right = st.columns(
        [5, 4, 4],
        gap="medium",
    )

    with left:
        conversation_panel(data, config)

    with middle:
        coaching_panel(data)

    with right:
        knowledge_panel(data)
