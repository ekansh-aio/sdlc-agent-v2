import os
import urllib3
import warnings
from dotenv import load_dotenv

import streamlit as st
from utils.session_manager import initialize_session_state
from services.jira_client import JiraClient

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

st.set_page_config(
    page_title="AI Helpers for QE",
    layout="wide",
    initial_sidebar_state="collapsed",
)

JIRA_ENDPOINT = os.getenv("JIRA_ENDPOINT", "")
initialize_session_state()

if "jira" not in st.session_state:
    st.session_state.jira = JiraClient(JIRA_ENDPOINT)
jira = st.session_state.jira

# ── Route ─────────────────────────────────────────────────────────────────────
if not st.session_state.get("jira_auth_popup_actioned", False):
    from screens.landing import render as landing
    landing(jira)

elif st.session_state.get("jira_user_authenticated", False):
    from screens.dashboard_jira import render as jira_dash
    jira_dash(jira)

else:
    from screens.dashboard_guest import render as guest_dash
    guest_dash(jira)
