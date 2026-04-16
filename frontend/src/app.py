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
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

JIRA_ENDPOINT = os.getenv("JIRA_ENDPOINT", "")
initialize_session_state()

if "jira" not in st.session_state:
    st.session_state.jira = JiraClient(JIRA_ENDPOINT)


# ── Page callables ─────────────────────────────────────────────────────────────
def _landing():
    from screens.landing import render
    render(st.session_state.jira)

def _guest():
    from screens.dashboard_guest import render
    render(st.session_state.jira)

def _jira_dash():
    from screens.dashboard_jira import render
    render(st.session_state.jira)


# ── Register all pages with stable URL paths ───────────────────────────────────
pg_landing = st.Page(_landing,   title="Home",           icon="🏠", url_path="landing",         default=True)
pg_guest   = st.Page(_guest,     title="Dashboard",      icon="⚡", url_path="dashboard")
pg_jira    = st.Page(_jira_dash, title="Jira Dashboard", icon="🔗", url_path="jira-dashboard")

pg = st.navigation([pg_landing, pg_guest, pg_jira], position="hidden")

# ── Auth-gated redirect ────────────────────────────────────────────────────────
auth_actioned = st.session_state.get("jira_auth_popup_actioned", False)
jira_authed   = st.session_state.get("jira_user_authenticated",  False)

if not auth_actioned:
    target = pg_landing
elif jira_authed:
    target = pg_jira
else:
    target = pg_guest

if pg.url_path != target.url_path:
    st.switch_page(target)
    st.stop()

pg.run()
