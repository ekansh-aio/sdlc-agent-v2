import json
import streamlit as st
from components.widgets.clipboard_btn import clipboard_button
from components.widgets.star_rating import star_rating
from components.dialogs.agent_chat import agent_chat_dialog


def response_card(
    label: str,
    response_text: str,
    agent_conversation: list,
    edit_key: str,
    on_push=None,        # callable(jira_id) or None
    jira_id: str = None,
    push_status: bool = False,
    jira_base_url: str = "",
):
    """
    Unified response card:
      - Displays / edits AI output
      - Copy, Analyze Agents, Edit/Save, optional Approve & Push
      - Star rating
    """
    if edit_key not in st.session_state:
        st.session_state[edit_key] = False
    content_key = f"{edit_key}__content"
    # Always sync the stored content when not in edit mode so new agent
    # responses are reflected immediately on re-render.
    if content_key not in st.session_state or not st.session_state.get(edit_key):
        st.session_state[content_key] = response_text

    with st.expander(label, expanded=True):
        with st.container(border=True):
            # ── Content area ──
            if st.session_state[edit_key]:
                edited = st.text_area(
                    "Edit response",
                    value=st.session_state[content_key],
                    height=280,
                    key=f"{edit_key}__area",
                )
                st.session_state[content_key] = edited
            else:
                display = st.session_state[content_key].replace("\n", "<br>")
                st.markdown(display, unsafe_allow_html=True)

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # ── Action row ──
            cols = st.columns(4 if jira_id else 3)

            with cols[0]:
                if st.button("Agents", key=f"{edit_key}__agents",
                             help="View agent conversation chain"):
                    agent_chat_dialog(agent_conversation)

            with cols[1]:
                clipboard_button(json.dumps(st.session_state[content_key]))

            with cols[2]:
                label_btn = "Save" if st.session_state[edit_key] else "Edit"
                if st.button(label_btn, key=f"{edit_key}__toggle"):
                    st.session_state[edit_key] = not st.session_state[edit_key]
                    st.rerun()

            if jira_id and on_push:
                with cols[3]:
                    if st.button("Push to Jira", key=f"{edit_key}__push", type="primary"):
                        st.session_state[f"{edit_key}__confirm"] = True

                if st.session_state.get(f"{edit_key}__confirm", False):
                    st.markdown(f"""
                    <div style="background:rgba(56,139,253,0.08);border:1px solid rgba(56,139,253,0.25);
                        border-radius:8px;padding:10px 14px;margin:8px 0;font-size:13px;color:#8b949e;">
                        Push <strong style="color:#e6edf3">{jira_id}</strong> to Jira?
                    </div>
                    """, unsafe_allow_html=True)
                    c1, c2, _ = st.columns([1, 1, 4])
                    with c1:
                        if st.button("Yes", key=f"{edit_key}__yes", type="primary"):
                            on_push(jira_id, st.session_state[content_key])
                            st.session_state[f"{edit_key}__confirm"] = False
                    with c2:
                        if st.button("No", key=f"{edit_key}__no"):
                            st.session_state[f"{edit_key}__confirm"] = False
                            st.rerun()

                if push_status and jira_base_url:
                    st.success(f"Pushed — [View {jira_id} in Jira]({jira_base_url}browse/{jira_id})")

            # ── Rating ──
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            star_rating("Rate this response:", f"{edit_key}__rating")
