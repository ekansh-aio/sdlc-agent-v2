import streamlit as st
from components.widgets.health_panel import health_panel
from components.dialogs.jira_login import jira_login_dialog

HELPER_RAS = "Requirement Analysis & Standardization"
HELPER_TCG = "Test Case Generator"


def guest_sidebar(jira):
    with st.sidebar:
        # ── Back to landing ──
        if st.button("← Back to start", key="sb_back", use_container_width=True):
            st.session_state.jira_auth_popup_actioned = False
            st.session_state.selected_helper = None
            st.session_state.free_text_input = None
            st.session_state.rewritten_content = {}
            st.rerun()

        st.markdown('<div class="sb-section-label">Choose a Helper</div>', unsafe_allow_html=True)

        ras_sel = st.session_state.get("selected_helper") == HELPER_RAS
        tcg_sel = st.session_state.get("selected_helper") == HELPER_TCG

        if st.button(
            "Requirement Analysis",
            key="nav_ras", use_container_width=True,
            type="primary" if ras_sel else "secondary",
            help="Refine raw requirements into INVEST-compliant user stories",
        ):
            st.session_state.selected_helper     = HELPER_RAS
            st.session_state.selected_input_type = None
            st.session_state.rewritten_content   = {}
            st.session_state.free_text_input     = None
            st.session_state.show_jira_login     = False
            st.rerun()

        if st.button(
            "Test Case Generator",
            key="nav_tcg", use_container_width=True,
            type="primary" if tcg_sel else "secondary",
            help="Generate Manual or BDD/Cucumber test cases",
        ):
            st.session_state.selected_helper     = HELPER_TCG
            st.session_state.selected_input_type = None
            st.session_state.rewritten_content   = {}
            st.session_state.free_text_input     = None
            st.session_state.show_jira_login     = False
            st.rerun()

        if tcg_sel:
            with st.container(border=True):
                st.markdown('<div class="sb-section-label" style="margin-top:0">Test Case Type</div>', unsafe_allow_html=True)
                st.session_state.tcg_selected_btn = st.radio(
                    "Test Case Type", ["Manual", "Automated"], index=0,
                    key="tcg_type_radio", horizontal=True,
                    label_visibility="collapsed",
                )

        # ── Jira promo ──
        st.markdown('<div class="sb-jira-promo"><b>Want Jira integration?</b><br>Connect to pick tickets and push results directly.</div>', unsafe_allow_html=True)

        if "show_jira_login" not in st.session_state:
            st.session_state.show_jira_login = False

        # Inject scoped teal style: the <style> + next sibling button pattern
        st.markdown("""
        <style>
        /* Connect to Jira button — teal gradient via adjacent sibling of marker */
        #jira-connect-marker + div [data-testid="stBaseButton-primary"] button,
        #jira-connect-marker ~ div [data-testid="stBaseButton-primary"] button {
            background: linear-gradient(135deg,#1f8a70 0%,#12b886 100%) !important;
            border: none !important;
            box-shadow: 0 2px 10px rgba(18,184,134,0.28) !important;
        }
        #jira-connect-marker + div [data-testid="stBaseButton-primary"] button:hover,
        #jira-connect-marker ~ div [data-testid="stBaseButton-primary"] button:hover {
            background: linear-gradient(135deg,#2aa88a 0%,#20c997 100%) !important;
            box-shadow: 0 4px 18px rgba(18,184,134,0.40) !important;
        }
        </style>
        <span id="jira-connect-marker" style="display:none"></span>
        """, unsafe_allow_html=True)
        if st.button("Connect to Jira", key="sb_connect_jira",
                     use_container_width=True, type="primary"):
            st.session_state.show_jira_login = True
            st.rerun()

        st.markdown('<hr style="border-color:rgba(255,255,255,0.06);margin:12px 0">', unsafe_allow_html=True)
        health_panel()

        if st.session_state.show_jira_login:
            jira_login_dialog(jira)
