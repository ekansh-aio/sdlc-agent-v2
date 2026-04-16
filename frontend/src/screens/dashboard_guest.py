"""
Guest dashboard — no Jira account.
Sidebar: RAS · TCG · Connect Jira (bottom)
Main: free-text only for whichever helper is selected (default RAS)
"""
import streamlit as st
from theme import load_theme, landing_gradient
from components.layout.header import app_header
from components.layout.sidebar_guest import guest_sidebar
from views.ras_view import ras_free_text
from views.tcg_view import tcg_free_text

HELPER_RAS = "Requirement Analysis & Standardization"
HELPER_TCG = "Test Case Generator"


def render(jira):
    load_theme()
    st.markdown("""<style>
    #MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],
    [data-testid="stStatusWidget"],[data-testid="stAppDeployButton"],.stDeployButton
    {display:none!important}
    </style>""", unsafe_allow_html=True)
    landing_gradient()
    app_header()

    # Default to RAS on first load
    if not st.session_state.get("selected_helper"):
        st.session_state.selected_helper = HELPER_RAS

    guest_sidebar(jira)

    helper = st.session_state.get("selected_helper", HELPER_RAS)

    # ── Breadcrumb ──
    short = "RAS" if helper == HELPER_RAS else "TCG"
    st.markdown(f"""
    <div style="display:inline-flex;align-items:center;gap:6px;
        font-size:11px;color:#6e7681;margin-bottom:20px;
        font-family:'Cascadia Code','Consolas',monospace;">
        <span style="color:#388bfd;font-weight:700">{short}</span>
        <span style="color:rgba(255,255,255,0.2)">›</span>
        <span>Free Text</span>
        {'<span style="color:rgba(255,255,255,0.2)">›</span><span>' + st.session_state.get("tcg_selected_btn","Manual") + '</span>' if helper == HELPER_TCG else ''}
    </div>
    """, unsafe_allow_html=True)

    if helper == HELPER_RAS:
        ras_free_text()
    elif helper == HELPER_TCG:
        tcg_free_text()
