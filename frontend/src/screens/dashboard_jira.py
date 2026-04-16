"""
Jira dashboard — authenticated user.
Sidebar: RAS · TCG · input type (Free Text / Jira Ticket) · ticket picker
Main: view for the selected helper + input type combination
"""
import streamlit as st
from theme import load_theme, landing_gradient
from components.layout.header import app_header
from components.layout.sidebar_jira import jira_sidebar
from views.ras_view import ras_free_text, ras_jira
from views.tcg_view import tcg_free_text, tcg_jira

HELPER_RAS = "Requirement Analysis & Standardization"
HELPER_TCG = "Test Case Generator"
INPUT_FREE = "Free Text Requirement"
INPUT_JIRA = "Jira ID"


def render(jira):
    load_theme()
    st.markdown("""<style>
    #MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],
    [data-testid="stStatusWidget"],[data-testid="stAppDeployButton"],.stDeployButton
    {display:none!important}
    </style>""", unsafe_allow_html=True)
    landing_gradient()
    app_header()

    if not st.session_state.get("selected_helper"):
        st.session_state.selected_helper = HELPER_RAS

    jira_sidebar(jira)

    helper   = st.session_state.get("selected_helper", HELPER_RAS)
    inp_type = st.session_state.get("selected_input_type", INPUT_FREE)

    # ── Reset content cache on input type change ──
    if st.session_state.get("_prev_input_type") != inp_type:
        st.session_state.rewritten_content    = {}
        st.session_state.pushed_status        = {}
        st.session_state.free_text_input      = None
        st.session_state.free_text_response   = None
        st.session_state._prev_input_type     = inp_type

    # ── Breadcrumb ──
    short     = "RAS" if helper == HELPER_RAS else "TCG"
    inp_short = "Jira Tickets" if inp_type == INPUT_JIRA else "Free Text"
    st.markdown(f"""
    <div style="display:inline-flex;align-items:center;gap:6px;
        font-size:11px;color:#6e7681;margin-bottom:20px;
        font-family:'Cascadia Code','Consolas',monospace;">
        <span style="color:#388bfd;font-weight:700">{short}</span>
        <span style="color:rgba(255,255,255,0.2)">›</span>
        <span>{inp_short}</span>
        {'<span style="color:rgba(255,255,255,0.2)">›</span><span>' + st.session_state.get("tcg_selected_btn","Manual") + '</span>' if helper == HELPER_TCG else ''}
    </div>
    """, unsafe_allow_html=True)

    # ── Route to correct view ──
    if helper == HELPER_RAS:
        if inp_type == INPUT_JIRA:
            ras_jira(jira)
        else:
            ras_free_text()
    elif helper == HELPER_TCG:
        if inp_type == INPUT_JIRA:
            tcg_jira(jira)
        else:
            tcg_free_text()
