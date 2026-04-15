"""
RAS (Requirement Analysis & Standardization) view.
Supports two modes:
  - free_text: user pastes raw requirement
  - jira: content fetched from selected Jira tickets
"""
import re
import os
import requests
import streamlit as st

from services.agent_client import call_agent
from utils.formatters import is_garbage_input, parse_ras_fields
from components.widgets.response_card import response_card

JIRA_ENDPOINT = os.getenv("JIRA_ENDPOINT", "").rstrip("/") + "/"
PROJ_KEY      = os.getenv("PROJ_KEY", "")


# ── Jira helpers ──────────────────────────────────────────────────────────────

def _fetch_jira_issue(jira_id: str, headers: dict) -> dict:
    url  = f"{JIRA_ENDPOINT}rest/api/2/issue/{jira_id}"
    resp = requests.get(url, headers=headers, verify=False)
    if resp.status_code != 200:
        raise Exception(f"{resp.status_code} — {resp.text}")
    data = resp.json()
    if data["fields"]["issuetype"]["name"].lower() != "story":
        raise ValueError(f"{jira_id} is not a Story.")
    st.session_state[f"epic_id_{jira_id}"] = data["fields"].get("customfield_10100", "") or ""
    return {
        "key":                data["key"],
        "summary":            data["fields"]["summary"],
        "description":        data["fields"].get("description", ""),
        "acceptance_criteria":data["fields"].get("customfield_12077", "Not Given"),
    }


def _push_ras(jira_id: str, content: str):
    title = st.session_state.get(f"ras_title_{jira_id}", "")
    payload = {
        "title": title, "description": content,
        "acceptance_criteria": content,
        "base_url": JIRA_ENDPOINT, "proj_key": PROJ_KEY,
        "jira_id": jira_id, "helper_name": "RAS", "activity": "PushtoJira",
        "jira_username": st.session_state.get("jira_username"),
        "jira_password": st.session_state.get("jira_password"),
    }
    with st.spinner("Pushing to Jira..."):
        body = call_agent(payload)
    if body and "status_code" in body:
        sc  = body["status_code"]
        msg = body.get("response_msg", "Done")
        if sc < 300:
            st.session_state.pushed_status[jira_id] = True
            st.success(f"{jira_id}: {msg}")
        else:
            st.error(f"Push failed ({sc}): {msg}")
    else:
        st.error("Could not reach Azure Function App.")
    st.rerun()


# ── Free-text RAS ─────────────────────────────────────────────────────────────

def ras_free_text():
    st.markdown("""
    <div style="margin-bottom:16px">
        <h4 style="color:#e6edf3;margin:0 0 6px;font-size:16px;font-weight:700;">
            Requirement Analysis & Standardization
        </h4>
        <p style="color:#8b949e;font-size:13px;margin:0;line-height:1.6;">
            Paste a raw requirement below. The AI agent will rewrite it as an
            INVEST-compliant user story with acceptance criteria, priority, and effort.
        </p>
    </div>
    """, unsafe_allow_html=True)

    user_input = st.chat_input("Describe your requirement...")

    if user_input:
        if len(user_input.strip().split()) < 3 or is_garbage_input(user_input):
            st.warning("Input too short or invalid — at least 3 meaningful words required.")
            st.session_state.invalid_len_input = True
        else:
            st.session_state.invalid_len_input  = False
            st.session_state.free_text_input    = user_input
            st.session_state.free_text_response = None
            st.session_state.rewritten_content  = {}

    free_text = st.session_state.get("free_text_input")
    if not free_text or st.session_state.get("invalid_len_input", False):
        return

    with st.expander("Your Requirement", expanded=False):
        st.session_state.free_text_input = st.text_area(
            "Edit before running", value=free_text, height=160, key="ras_edit_input"
        )

    if st.button("Run RAS", key="ras_run", type="primary"):
        with st.spinner("Running Requirement Analysis agent..."):
            body = call_agent({
                "helper_name": "RAS",
                "requirement": st.session_state.free_text_input,
            })
        if not body or "response" not in body:
            st.session_state.free_text_response          = "Could not connect to Function App."
            st.session_state.free_text_agent_conversation = []
        else:
            st.session_state.free_text_response           = body["response"]
            st.session_state.free_text_agent_conversation = body.get("chat_history", [])

    if st.session_state.get("free_text_response"):
        response_card(
            label="RAS Output",
            response_text=st.session_state.free_text_response,
            agent_conversation=st.session_state.get("free_text_agent_conversation", []),
            edit_key="ras_free_edit",
        )


# ── Jira-ticket RAS ───────────────────────────────────────────────────────────

def ras_jira(jira):
    jira_ids = st.session_state.get("jira_selected", [])

    st.markdown("""
    <div style="margin-bottom:16px">
        <h4 style="color:#e6edf3;margin:0 0 6px;font-size:16px;font-weight:700;">
            Requirement Analysis & Standardization
        </h4>
        <p style="color:#8b949e;font-size:13px;margin:0;line-height:1.6;">
            Selected Jira stories will be rewritten as INVEST-compliant user stories.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if not jira_ids:
        st.info("Select one or more Jira tickets from the sidebar to begin.")
        return

    # Sync removed tickets
    prev = set(st.session_state.get("previous_jira_selected", []))
    curr = set(jira_ids)
    for removed in prev - curr:
        st.session_state.rewritten_content.pop(removed, None)
        st.session_state.pushed_status.pop(removed, None)
    st.session_state.previous_jira_selected = list(curr)

    jira_content = {}
    for jira_id in jira_ids:
        try:
            d = _fetch_jira_issue(jira_id, jira.headers)
            content = (
                f"**Summary**: {d['summary']}\n\n"
                f"**Description**:\n\n{d['description']}\n\n"
                f"**Acceptance Criteria**:\n\n{d['acceptance_criteria']}"
            )
            with st.expander(f"{d['key']} — {d['summary']}", expanded=False):
                st.markdown(content)
            jira_content[jira_id] = content
        except Exception as e:
            st.error(f"{jira_id}: {e}")

    if st.button("Run RAS on selected tickets", key="ras_jira_run", type="primary"):
        for jira_id in jira_ids:
            original = jira_content.get(jira_id)
            if not original:
                continue
            with st.spinner(f"Processing {jira_id}..."):
                body = call_agent({"helper_name": "RAS", "requirement": original})
            if not body or "response" not in body:
                st.session_state.rewritten_content[jira_id]           = "Could not connect to Function App."
                st.session_state[f"ras_conv_{jira_id}"]               = []
            else:
                raw  = body["response"]
                convo = body.get("chat_history", [])
                title, desc_md, ac, priority, effort = parse_ras_fields(raw)
                epic  = st.session_state.get(f"epic_id_{jira_id}", "")
                if epic and f"{epic}-" not in title:
                    title = f"{epic}-{title}"
                st.session_state[f"ras_title_{jira_id}"] = title
                st.session_state.rewritten_content[jira_id] = (
                    f"**Title:** {title}\n\n{desc_md}\n\n{ac}\n\n"
                    f"**Priority:** {priority}\n\n**Estimated Effort:** {effort}"
                )
                st.session_state[f"ras_conv_{jira_id}"] = convo
            st.session_state.pushed_status[jira_id] = False

    for jira_id in jira_ids:
        content = st.session_state.rewritten_content.get(jira_id)
        if not content:
            continue
        response_card(
            label=f"RAS Output — {jira_id}",
            response_text=content,
            agent_conversation=st.session_state.get(f"ras_conv_{jira_id}", []),
            edit_key=f"ras_jira_{jira_id}",
            on_push=_push_ras,
            jira_id=jira_id,
            push_status=st.session_state.pushed_status.get(jira_id, False),
            jira_base_url=JIRA_ENDPOINT,
        )
