
"""Post-interaction report with metrics and coaching recommendations."""

import streamlit as st

from backend.services import storage


def render():
    """Display session metrics, sentiment trends, and recommendations."""
    session = st.session_state

    st.markdown(
        "<h1>Post-Interaction Report</h1>"
        '<p class="page-subtitle">Review your session performance '
        "and coaching feedback below.</p>",
        unsafe_allow_html=True,
    )

    analyses = session.analyses

    if not analyses:
        st.info("No customer messages were analysed in this session.")
    else:
        frustration = [item["frustration"] for item in analyses]
        peak_risk = max(item["risk"] for item in analyses)
        tone_scores = [item["score"] for item in session.tone] or [0]

        quality = int(
            max(
                0,
                min(
                    100,
                    100
                    - frustration[-1] * 0.5
                    - peak_risk * 0.2
                    + sum(tone_scores) / len(tone_scores) * 0.2,
                ),
            )
        )

        # Display the main session metrics.
        with st.container(border=True):
            col1, col2, col3 = st.columns(3)
            col1.metric("Resolution quality", f"{quality}/100")
            col2.metric("Peak escalation risk", f"{peak_risk}%")
            col3.metric("Customer turns", len(analyses))

        st.write("")

        # Show how frustration and escalation risk changed.
        with st.container(border=True):
            st.markdown(
                '<p class="section-heading">Sentiment Journey</p>',
                unsafe_allow_html=True,
            )
            st.line_chart(
                {
                    "Frustration %": frustration,
                    "Escalation risk %": [
                        item["risk"] for item in analyses
                    ],
                }
            )

        st.write("")

        # Provide recommendations for improving customer support.
        with st.container(border=True):
            st.markdown(
                '<p class="section-heading">'
                "Coaching Recommendations</p>",
                unsafe_allow_html=True,
            )
            st.write(
                "- Open with empathy when frustration rises above 50%.\n"
                "- Give a concrete next step and timeline in every reply.\n"
                "- Offer a supervisor early when the customer mentions "
                "cancelling or a refund."
            )

        # Allow the user to review the full conversation.
        with st.expander("Full transcript"):
            for message in session.messages:
                st.write(
                    f"**{message['role'].title()}:** {message['text']}"
                )

    st.write("")

    col_rep_new, col_rep_back = st.columns(2)
    with col_rep_new:
        if st.button("Start new session", type="primary", use_container_width=True):
            session.view = "setup"
            session.sid = None
            st.query_params.clear()
            if "page_dashboard" in st.session_state:
                st.switch_page(st.session_state["page_dashboard"])
            else:
                st.rerun()
    with col_rep_back:
        if st.button("Return to Console", use_container_width=True):
            session.view = "console"
            st.rerun()
