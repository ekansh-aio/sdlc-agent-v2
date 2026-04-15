import json as _json
import time
import streamlit as st
from theme import load_chat_css


def _to_markdown(content: str) -> str:
    """
    Ensure content renders correctly as markdown.
    - Raw JSON arrays/objects → fenced ```json``` block (pretty-printed)
    - YAML-ish agent output blocks (finalResult: / finalData:) → fenced ``` block
    - Strings that already have code fences → pass through unchanged
    - Everything else → return as-is (Streamlit markdown handles headers, bold, lists)
    """
    stripped = content.strip()

    # Already fenced — don't double-wrap
    if stripped.startswith("```"):
        return content

    # Raw JSON array or object
    if stripped.startswith(("[", "{")) and stripped.endswith(("]", "}")):
        try:
            parsed = _json.loads(stripped)
            return "```json\n" + _json.dumps(parsed, indent=2) + "\n```"
        except (ValueError, _json.JSONDecodeError):
            return "```\n" + stripped + "\n```"

    # Agent output block with finalResult / finalData (not valid markdown)
    if stripped.startswith(("finalResult:", "finalData:")):
        return "```\n" + stripped + "\n```"

    # Regular markdown / prose — return unchanged so Streamlit renders it
    return content


_AGENT_COLORS = {
    "user":                            "#58a6ff",
    "request_handler_agent":           "#58a6ff",
    "analyser_agent":                  "#a371f7",
    "reviewer_agent":                  "#79c0ff",
    "final_response_generator_agent":  "#3fb950",
    "requesthandleragent":             "#58a6ff",
    "analyseragent":                   "#a371f7",
    "revieweragent":                   "#79c0ff",
    "finalresponsegeneratoragent":     "#3fb950",
    # RAS naming variants
    "requesthandler":                  "#58a6ff",
    "analysisagent":                   "#a371f7",
    "finalresponsegenerator":          "#3fb950",
}
_DEFAULT_AGENT_COLOR = "#8b949e"


@st.dialog("Agent Conversation", width="large")
def agent_chat_dialog(chat_history):
    load_chat_css()
    if not chat_history:
        st.info("No agent conversation recorded for this response.")
        return
    try:
        for message in chat_history:
            content = message.get("content")
            if not content:
                continue
            role   = message.get("role", "")
            source = message.get("source", "Unknown")
            name   = role if role else source
            is_user = name.lower() == "user"

            with st.spinner(f"{name} is thinking..."):
                time.sleep(0.10)

            color = _AGENT_COLORS.get(name.lower(), _DEFAULT_AGENT_COLOR)
            icon  = "→" if is_user else "◎"

            # Name badge
            st.markdown(
                f'<div class="name-label" style="color:{color}">{icon} {name.upper()}</div>',
                unsafe_allow_html=True,
            )

            # Content — properly rendered markdown / code
            text = content if isinstance(content, str) else _json.dumps(content, indent=2)
            st.markdown(_to_markdown(text))

            st.markdown(
                "<hr style='border:none;border-top:1px solid rgba(255,255,255,0.06);margin:6px 0 14px'>",
                unsafe_allow_html=True,
            )

    except Exception:
        st.warning("Could not load agent conversation.")
