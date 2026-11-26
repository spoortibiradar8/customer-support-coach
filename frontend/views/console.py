
"""Three-panel live coaching console."""

import streamlit as st

from backend.services import pipeline_stub as pipe
from backend.services import rag_stub, storage
from backend.services.validation import validate_message

RISK_ALERT = 70


def get_console_data(sid):
    key = f"console_data_{sid}"
    if key not in st.session_state:
        st.session_state[key] = {
            "messages": [],
            "analyses": [],
            "tone": [],
            "replay_idx": 0,
        }
    return st.session_state[key]


def add_message(data, role, text, config):
    data["messages"].append({"role": role, "text": text})

    if role == "customer":
        analysis = pipe.analyze_turn(
            text,
            data["messages"],
            config,
        )
        data["analyses"].append(analysis)

    elif role == "agent":
        customer_messages = [
            m["text"] for m in data["messages"]
            if m["role"] == "customer"
        ]
        last_customer = customer_messages[-1] if customer_messages else None

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


def customer_count(data):
    return sum(
        m["role"] == "customer"
        for m in data["messages"]
    )


def reply_form(data, config):
    with st.form(
        f"reply_{config['session_id']}_{len(data['messages'])}",
        clear_on_submit=True,
    ):
        reply = st.text_area("Your reply to the customer", height=90)
        submitted = st.form_submit_button(
            "Send reply",
            use_container_width=True,
        )

        if submitted:
            error = validate_message(reply, "Reply")
            if error:
                st.error(error)
            else:
                add_message(data, "agent", reply.strip(), config)
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
                error = validate_message(message, "Customer message")
                if error:
                    st.error(error)
                else:
                    add_message(
                        data, "customer", message.strip(), config
                    )
                    st.rerun()

        if data["messages"] and data["messages"][-1]["role"] == "customer":
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
            st.rerun()

        if col_restart.button(
            "Restart replay",
            use_container_width=True,
        ):
            data["messages"] = []
            data["analyses"] = []
            data["tone"] = []
            data["replay_idx"] = 0
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

    st.write(f"**Why:** {analysis['risk_reason']}")

    if analysis["risk"] >= RISK_ALERT:
        st.warning(
            f"**Recommended strategy:** {analysis['strategy']}"
        )

    with st.container(border=True):
        st.markdown("**Suggested response**")
        st.write(analysis["suggestion"])

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
        st.caption("Relevant articles appear after a customer message.")
        return

    chunks = data["analyses"][-1]["chunks"]

    if not chunks:
        st.info("No relevant knowledge chunks found.")
        return

    for index, chunk in enumerate(chunks, 1):
        with st.container(border=True):
            source = chunk.get("source", chunk.get("doc_name", "Document"))
            page = chunk.get("page", "N/A")
            score = chunk.get("score", 0)

            st.markdown(
                f"**#{index} — {source}** — Page {page}"
            )
            st.caption(f"Relevance score: {score}")

            preview = chunk.get("text", "")
            st.write(preview[:350])


def render():
    st.markdown("<h1>Live Coaching Console</h1>", unsafe_allow_html=True)

    all_sessions = storage.list_sessions()

    if not all_sessions:
        st.info("No sessions available. Create a session from Dashboard.")
        return

    session_ids = [item[0] for item in all_sessions]

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
