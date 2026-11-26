"""Three-panel live coaching console for conversation, coaching, and knowledge."""

import streamlit as st

from backend.config import REPLAY_SAMPLE_PATH
from backend.services import pipeline_stub as pipe
from backend.services import rag_stub, storage, validation
from backend.services.validation import validate_message

# Show a prominent warning when escalation risk reaches this value.
RISK_ALERT = 70


def load_session_into_state(sid: str) -> bool:
    """Load a session from storage into st.session_state."""
    data = storage.load(sid)
    if not data:
        return False
    session = st.session_state
    session.sid = sid
    mode = data.get("mode", "Simulator")
    replay_script = data.get("replay_transcript") or data.get("replay_script", [])
    if mode == "Replay" and not replay_script and REPLAY_SAMPLE_PATH.exists():
        replay_script = validation.parse_transcript(REPLAY_SAMPLE_PATH.read_text(encoding="utf-8"))

    session.config = {
        "mode": mode,
        "product": data.get("product", "Acme Online Store"),
        "scenario": data.get("scenario", ""),
        "persona": data.get("persona", "Calm"),
        "max_turns": data.get("max_turns", 5),
        "replay_script": replay_script,
    }
    session.messages = list(data.get("messages", []))
    session.analyses = list(data.get("analyses", []))
    session.tone = list(data.get("tone", []))
    session.replay_idx = data.get("replay_idx", 0)
    session.view = "console"
    return True


def _ensure_session_initialized():
    """Ensure st.session_state is safely populated with a valid active session."""
    session = st.session_state
    sid = getattr(session, "sid", None)
    config = getattr(session, "config", None)

    if not sid or not config:
        recent = storage.list_sessions(limit=1)
        if recent:
            load_session_into_state(recent[0][0])
        else:
            default_sid = storage.new_id()
            session.sid = default_sid
            session.config = {
                "mode": "Simulator",
                "product": "Acme Online Store",
                "scenario": "Customer was charged twice for order #4821 and wants the duplicate payment refunded.",
                "persona": "Frustrated",
                "max_turns": 5,
                "replay_script": [],
            }
            session.messages = []
            session.analyses = []
            session.tone = []
            session.replay_idx = 0
            session.view = "console"
            storage.save(session)

    if getattr(session, "config", {}).get("mode") == "Replay" and not session.config.get("replay_script"):
        if REPLAY_SAMPLE_PATH.exists():
            session.config["replay_script"] = validation.parse_transcript(REPLAY_SAMPLE_PATH.read_text(encoding="utf-8"))

    if not hasattr(session, "messages") or session.messages is None:
        session.messages = []
    if not hasattr(session, "analyses") or session.analyses is None:
        session.analyses = []
    if not hasattr(session, "tone") or session.tone is None:
        session.tone = []
    if not hasattr(session, "replay_idx") or session.replay_idx is None:
        session.replay_idx = 0
    if not hasattr(session, "view") or session.view is None:
        session.view = "console"


def add_message(role, text):
    """Append a message, analyze customer messages, and save the session."""
    session = st.session_state
    session.messages.append({"role": role, "text": text})

    if role == "customer":
        session.analyses.append(
            pipe.analyze_turn(text, session.messages, session.config)
        )
    else:
        customer_msg = None
        for m in reversed(session.messages):
            if m.get("role") == "customer":
                customer_msg = m.get("text")
                break

        latest_analysis = session.analyses[-1] if session.analyses else {}
        policies = latest_analysis.get("chunks")
        product = session.config.get("product") if isinstance(session.config, dict) else None

        session.tone.append(
            pipe.evaluate_agent_reply(
                text,
                customer_message=customer_msg,
                history=session.messages,
                policies=policies,
                product_name=product,
            )
        )

    storage.save(session)


def n_customer():
    """Count customer messages in the current conversation."""
    return sum(
        message["role"] == "customer"
        for message in st.session_state.messages
    )


def conversation_panel():
    """Display the conversation and controls for the selected mode."""
    session = st.session_state
    config = session.config
    mode = config.get("mode", "Simulator")

    st.markdown(
        '<p class="section-heading">Conversation</p>',
        unsafe_allow_html=True,
    )

    conversation_box = st.container(height=380, border=True)
    with conversation_box:
        if not session.messages:
            if mode == "Simulator":
                st.caption("No messages yet. Click 'Start simulation' below to begin.")
            elif mode == "Manual":
                st.caption("No messages yet. Click 'Start session' below to begin with the customer issue.")
            else:
                st.caption("No messages yet. Click 'Start replay' below to begin transcript playback.")

        for message in session.messages:
            chat_role = (
                "user" if message["role"] == "customer" else "assistant"
            )
            with st.chat_message(chat_role):
                st.write(message["text"])

    if mode == "Simulator":
        if not session.messages:
            if st.button(
                "Start simulation",
                type="primary",
                use_container_width=True,
            ):
                add_message("customer", pipe.simulate_customer(config, 0))
                st.rerun()
        else:
            reply_form("Your reply to the customer", after=simulate_next)

    elif mode == "Manual":
        if not session.messages:
            scenario_text = config.get("scenario", "").strip()
            if scenario_text:
                if st.button(
                    "Start session with customer issue",
                    type="primary",
                    use_container_width=True,
                ):
                    add_message("customer", scenario_text)
                    st.rerun()

                with st.expander("Or enter / paste custom customer message", expanded=False):
                    with st.form("manual_first_msg", clear_on_submit=True):
                        custom_text = st.text_area(
                            "Incoming customer message",
                            value=scenario_text,
                            height=80,
                        )
                        submitted = st.form_submit_button(
                            "Start session with custom message",
                            use_container_width=True,
                        )
                        if submitted:
                            error = validate_message(custom_text, "Customer message")
                            if error:
                                st.error(error)
                            else:
                                add_message("customer", custom_text.strip())
                                st.rerun()
            else:
                with st.form("manual_first_msg_empty", clear_on_submit=True):
                    custom_text = st.text_area(
                        "Paste incoming customer message to start session",
                        placeholder="Type customer message here...",
                        height=80,
                    )
                    submitted = st.form_submit_button(
                        "Start session",
                        type="primary",
                        use_container_width=True,
                    )
                    if submitted:
                        error = validate_message(custom_text, "Customer message")
                        if error:
                            st.error(error)
                        else:
                            add_message("customer", custom_text.strip())
                            st.rerun()
        else:
            last_role = session.messages[-1].get("role")
            if last_role == "customer":
                reply_form("Your reply to the customer")
            else:
                with st.form(f"customer_next_{len(session.messages)}", clear_on_submit=True):
                    next_text = st.text_area("Paste next customer message", height=80)
                    col_sub, col_sim = st.columns([2, 1])
                    sub = col_sub.form_submit_button(
                        "Add customer message",
                        type="primary",
                        use_container_width=True,
                    )
                    sim = col_sim.form_submit_button(
                        "Simulate AI reply",
                        use_container_width=True,
                    )
                    if sub:
                        err = validate_message(next_text, "Customer message")
                        if err:
                            st.error(err)
                        else:
                            add_message("customer", next_text.strip())
                            st.rerun()
                    elif sim:
                        add_message("customer", pipe.simulate_customer(config, n_customer()))
                        st.rerun()

    else:  # Replay mode
        script = config.get("replay_script", [])
        if not script and REPLAY_SAMPLE_PATH.exists():
            script = validation.parse_transcript(REPLAY_SAMPLE_PATH.read_text(encoding="utf-8"))
            config["replay_script"] = script
            session.config["replay_script"] = script

        index = session.replay_idx
        total = len(script)

        if not session.messages:
            if st.button(
                "Start replay",
                type="primary",
                use_container_width=True,
                disabled=total == 0,
            ):
                if script:
                    first_msg = script[0]
                    session.replay_idx = 1
                    add_message(first_msg["role"], first_msg["text"])
                    st.rerun()
        else:
            progress = min(index / total, 1.0) if total else 0
            st.progress(progress, text=f"Message {index} of {total}")

            col_next, col_restart = st.columns(2)

            btn_label = f"Next message ({index + 1}/{total})" if index < total else "Replay complete"
            if col_next.button(
                btn_label,
                type="primary",
                disabled=index >= total,
                use_container_width=True,
            ):
                message = script[index]
                session.replay_idx += 1
                add_message(message["role"], message["text"])
                st.rerun()

            if col_restart.button("Restart replay", use_container_width=True):
                session.messages = []
                session.analyses = []
                session.tone = []
                session.replay_idx = 0
                storage.save(session)
                st.rerun()

            if index >= total:
                st.success("Replay finished. Click 'End session' above to view the performance report.")


def simulate_next():
    """Add the next simulated customer message after an agent reply."""
    config = st.session_state.config
    customer_count = n_customer()
    max_turns = config.get("max_turns", 5)

    if customer_count < max_turns:
        add_message(
            "customer",
            pipe.simulate_customer(config, customer_count),
        )
    else:
        st.session_state.flash = (
            "Simulation limit reached. Click 'End session' to inspect the final performance report."
        )


def reply_form(label, after=None):
    """Display a form for the agent to submit a reply."""
    with st.form(
        f"reply_{len(st.session_state.messages)}",
        clear_on_submit=True,
    ):
        text = st.text_area(label, height=80)
        submitted = st.form_submit_button(
            "Send reply",
            use_container_width=True,
        )

        if submitted:
            error = validate_message(text, "Reply")
            if error:
                st.error(error)
            else:
                add_message("agent", text.strip())
                if after:
                    after()
                st.rerun()


def coaching_panel(analysis):
    """Show the latest sentiment, intent, escalation risk, and reply feedback."""
    st.markdown(
        '<p class="section-heading">Coaching Feed</p>',
        unsafe_allow_html=True,
    )

    if not analysis:
        st.info("Waiting for the first customer message...")
        return

    col_sentiment, col_intent = st.columns(2)
    col_sentiment.metric(
        "Sentiment",
        analysis["sentiment"],
        analysis["emotion"],
        delta_color="off",
    )
    col_intent.metric("Intent", analysis["intent"])

    st.caption(f"Frustration — {analysis['frustration']}%")
    st.progress(analysis["frustration"] / 100)

    risk_score = analysis.get("risk", 0)
    risk_level = str(analysis.get("risk_level", "low")).upper()
    requires_supervisor = analysis.get("requires_supervisor", False)
    flags = analysis.get("warning_flags", [])

    st.caption(f"Escalation risk — {risk_score}% ({risk_level})")
    st.progress(risk_score / 100)

    if flags:
        flag_pills = " ".join(f"`{f}`" for f in flags)
        st.markdown(f"**Flags:** {flag_pills}")

    if requires_supervisor:
        st.error("⚠️ **Supervisor / Lead Handover Advised**")

    st.write(f"**Why:** {analysis['risk_reason']}")

    if risk_score >= RISK_ALERT:
        st.warning(f"**De-escalation strategy:** {analysis['strategy']}")
        if analysis.get("suggested_de_escalation_phrase"):
            st.info(f"**Calming phrase:** \"{analysis['suggested_de_escalation_phrase']}\"")

    with st.container(border=True):
        st.markdown("**Suggested response**")
        st.write(analysis["suggestion"])

    session = st.session_state
    if session.tone:
        latest_tone = session.tone[-1]
        with st.container(border=True):
            st.markdown(
                f"**Your last reply — tone and clarity: "
                f"{latest_tone['score']}/100**"
            )
            for note in latest_tone["notes"]:
                st.write(note)


def knowledge_panel(analysis):
    """Show the most relevant knowledge-base chunks for the latest message."""
    st.markdown(
        '<p class="section-heading">Knowledge</p>',
        unsafe_allow_html=True,
    )

    if not analysis:
        st.caption("Relevant articles appear after each customer message.")
        return

    if rag_stub.stats()["total"] == 0:
        st.warning("Knowledge base is empty. Upload PDFs on the Dashboard.")
        return

    if not analysis["chunks"]:
        st.info("No relevant chunks found for this message.")
        return

    for index, chunk in enumerate(analysis["chunks"], 1):
        with st.container(border=True):
            st.markdown(
                f"**#{index} — {chunk['source']}** "
                f"— page {chunk['page']} "
                f'<span class="badge-orange">score {chunk["score"]}</span>',
                unsafe_allow_html=True,
            )

            preview = chunk["text"][:350]
            if len(chunk["text"]) > 350:
                preview += "..."
            st.caption(preview)


def render():
    """Render the page header and the three main console panels."""
    _ensure_session_initialized()
    session = st.session_state

    # If session is in report view, render the Post-Interaction Report
    if session.get("view") == "report":
        from frontend.views import report
        report.render()
        return

    config = session.config
    all_sessions = storage.list_sessions()
    session_options = [s[0] for s in all_sessions]
    if session.sid not in session_options:
        session_options = [session.sid] + session_options

    col_title, col_sel, col_new, col_end = st.columns([4, 3, 2, 2], gap="small")

    with col_title:
        st.markdown(
            "<h1 style='margin-bottom:2px; font-size:1.8rem;'>Live Coaching Console</h1>",
            unsafe_allow_html=True,
        )
        st.caption(
            f"Mode: **{config.get('mode', 'Simulator')}** · Product: **{config.get('product', 'Acme Online Store')}**"
        )

    with col_sel:
        current_idx = session_options.index(session.sid) if session.sid in session_options else 0
        chosen_sid = st.selectbox(
            "Select active session",
            options=session_options,
            index=current_idx,
            key="console_session_picker",
            label_visibility="collapsed",
        )
        if chosen_sid and chosen_sid != session.sid:
            load_session_into_state(chosen_sid)
            st.rerun()

    with col_new:
        if st.button("New session", use_container_width=True):
            session.view = "setup"
            if "page_dashboard" in st.session_state:
                st.switch_page(st.session_state["page_dashboard"])
            else:
                st.rerun()

    with col_end:
        if st.button(
            "End session",
            type="primary",
            use_container_width=True,
        ):
            session.view = "report"
            storage.save(session)
            st.rerun()

    if session.get("flash"):
        st.info(session.pop("flash"))

    analysis = session.analyses[-1] if session.analyses else None
    if analysis and analysis["risk"] >= RISK_ALERT:
        st.error(
            f"HIGH ESCALATION RISK ({analysis['risk']}%) — "
            f"{analysis['risk_reason']}"
        )

    left, middle, right = st.columns([5, 4, 4], gap="medium")

    with left:
        conversation_panel()

    # Refresh the latest analysis after the conversation panel renders.
    analysis = session.analyses[-1] if session.analyses else None

    with middle:
        coaching_panel(analysis)

    with right:
        knowledge_panel(analysis)
