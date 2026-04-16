"""
TCG (Test Case Generator) view.
Supports Manual and Automated (BDD/Cucumber) modes.
Two input modes: free text and Jira ticket.
"""
import re
import os
import requests
import streamlit as st

from services.agent_client import call_agent
from services.jira_client import _from_adf
from utils.formatters import is_garbage_input, fmt_tcg_response
from components.widgets.response_card import response_card

JIRA_ENDPOINT = os.getenv("JIRA_ENDPOINT", "").rstrip("/") + "/"
PROJ_KEY      = os.getenv("PROJ_KEY", "")


def _fetch_jira_issue(jira_id: str, headers: dict) -> dict:
    url  = f"{JIRA_ENDPOINT}rest/api/3/issue/{jira_id}"
    resp = requests.get(url, headers=headers, verify=False)
    if resp.status_code != 200:
        raise Exception(f"{resp.status_code} — {resp.text}")
    data = resp.json()
    if data["fields"]["issuetype"]["name"].lower() != "story":
        raise ValueError(f"{jira_id} is not a Story.")
    # API v3 returns description and custom fields as ADF — extract plain text
    return {
        "key":                data["key"],
        "summary":            data["fields"]["summary"],
        "description":        _from_adf(data["fields"].get("description")) or "",
        "acceptance_criteria":_from_adf(data["fields"].get("customfield_12077")) or "Not Given",
    }


def _push_tcg(jira_id: str, content: str):
    # reverse bold formatting for Jira
    plain = content
    for bold, orig in [
        ("**TestCaseID:** ",  "TestCaseID:"),
        ("**Summary:** ",     "Summary:"),
        ("**Description:** ", "Description:"),
        ("**Action:** ",      "Action:"),
        ("**Data:** ",        "Data:"),
        ("**Expected Result:** ", "Expected Result:"),
        ("**Priority:** ",    "Priority:"),
        ("**Manual Steps:** ","ManualSteps:"),
        ("**Cucumber Steps:** ","cucumber_steps:"),
    ]:
        plain = plain.replace(bold, orig)
    issue_data = plain.replace("<br>", "\n")
    payload = {
        "issue_type":    st.session_state.get("tcg_selected_btn", "Manual"),
        "input_type":    "jira_id",
        "request_data":  issue_data,
        "process_type":  "push_data",
        "base_url":      JIRA_ENDPOINT,
        "proj_key":      PROJ_KEY,
        "jira_id":       jira_id,
        "activity":      "PushtoJira",
        "jira_username": st.session_state.get("jira_username"),
        "jira_password": st.session_state.get("jira_password"),
        "helper_name":   "TCG",
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


def _mode_badge():
    mode = st.session_state.get("tcg_selected_btn", "Manual")
    color = "#388bfd" if mode == "Manual" else "#a371f7"
    st.markdown(f"""
    <span style="display:inline-flex;align-items:center;gap:5px;
        background:rgba(56,139,253,0.1);border:1px solid rgba(56,139,253,0.3);
        border-radius:100px;padding:3px 10px;font-size:11px;color:{color};
        font-weight:600;letter-spacing:.04em;margin-bottom:14px;font-family:monospace;">
        ● {mode}
    </span>
    """, unsafe_allow_html=True)


# ── Free-text TCG ─────────────────────────────────────────────────────────────

def tcg_free_text():
    st.markdown("""
    <div style="margin-bottom:16px">
        <h4 style="color:#e6edf3;margin:0 0 6px;font-size:16px;font-weight:700;">
            Test Case Generator
        </h4>
        <p style="color:#8b949e;font-size:13px;margin:0;line-height:1.6;">
            Paste a requirement or user story. The AI will generate structured test cases.
        </p>
    </div>
    """, unsafe_allow_html=True)
    _mode_badge()

    user_input = st.chat_input("Describe the feature to test...")

    if user_input:
        if len(user_input.strip().split()) < 3 or is_garbage_input(user_input):
            st.warning("Input too short or invalid.")
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
            "Edit before running", value=free_text, height=160, key="tcg_edit_input"
        )

    mode = st.session_state.get("tcg_selected_btn", "Manual")
    if st.button(f"Generate {mode} Test Cases", key="tcg_run", type="primary"):
        test_type = "text_manual" if mode == "Manual" else "text_automatic"
        with st.spinner("Running Test Case Generator agent..."):
            body = call_agent({
                "issue_type":   test_type,
                "input_type":   "text_input",
                "request_data": st.session_state.free_text_input,
                "process_type": "get_data",
                "helper_name":  "TCG",
            })
        if not body or "response" not in body:
            st.session_state.free_text_response           = "Could not connect to Function App."
            st.session_state.free_text_agent_conversation = []
        else:
            st.session_state.free_text_response           = fmt_tcg_response(body["response"]).replace("\n", "<br>")
            st.session_state.free_text_agent_conversation = body.get("chat_history", [])

    if st.session_state.get("free_text_response"):
        response_card(
            label="TCG Output",
            response_text=st.session_state.free_text_response,
            agent_conversation=st.session_state.get("free_text_agent_conversation", []),
            edit_key="tcg_free_edit",
        )


# ── Jira-ticket TCG ───────────────────────────────────────────────────────────

def tcg_jira(jira):
    jira_ids = st.session_state.get("jira_selected", [])

    st.markdown("""
    <div style="margin-bottom:16px">
        <h4 style="color:#e6edf3;margin:0 0 6px;font-size:16px;font-weight:700;">
            Test Case Generator
        </h4>
        <p style="color:#8b949e;font-size:13px;margin:0;line-height:1.6;">
            Select Jira stories from the sidebar to generate test cases.
        </p>
    </div>
    """, unsafe_allow_html=True)
    _mode_badge()

    if not jira_ids:
        st.info("Select one or more Jira tickets from the sidebar to begin.")
        return

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

    mode = st.session_state.get("tcg_selected_btn", "Manual")
    if st.button(f"Generate {mode} Test Cases", key="tcg_jira_run", type="primary"):
        for jira_id in jira_ids:
            original = jira_content.get(jira_id)
            if not original:
                continue
            pattern = r"\*\*(.*?)\*\*:\s*(.*?)(?=(\*\*|$))"
            matches = re.findall(pattern, original, re.DOTALL)
            req_data = {k.strip(): v.strip() for k, v, _ in matches}
            req_data["parent"] = jira_id
            with st.spinner(f"Processing {jira_id}..."):
                body = call_agent({
                    "issue_type":   mode,
                    "input_type":   "jira_id",
                    "request_data": str(req_data),
                    "process_type": "get_data",
                    "helper_name":  "TCG",
                })
            if not body or "response" not in body:
                st.session_state.rewritten_content[jira_id]  = "Could not connect to Function App."
                st.session_state[f"tcg_conv_{jira_id}"]      = []
            else:
                st.session_state.rewritten_content[jira_id]  = fmt_tcg_response(body["response"]).replace("\n", "<br>")
                st.session_state[f"tcg_conv_{jira_id}"]      = body.get("chat_history", [])
            st.session_state.pushed_status[jira_id] = False

    for jira_id in jira_ids:
        content = st.session_state.rewritten_content.get(jira_id)
        if not content:
            continue
        response_card(
            label=f"TCG Output — {jira_id}",
            response_text=content,
            agent_conversation=st.session_state.get(f"tcg_conv_{jira_id}", []),
            edit_key=f"tcg_jira_{jira_id}",
            on_push=_push_tcg,
            jira_id=jira_id,
            push_status=st.session_state.pushed_status.get(jira_id, False),
            jira_base_url=JIRA_ENDPOINT,
        )
