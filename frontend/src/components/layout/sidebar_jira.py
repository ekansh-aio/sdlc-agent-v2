import streamlit as st
from components.widgets.health_panel import health_panel

HELPER_RAS = "Requirement Analysis & Standardization"
HELPER_TCG = "Test Case Generator"
INPUT_FREE = "Free Text Requirement"
INPUT_JIRA = "Jira ID"


def _update_jira_selected():
    st.session_state.jira_selected = st.session_state.jira_multiselect


def jira_sidebar(jira):
    with st.sidebar:
        # ── Back link ──
        if st.button("← Back to start", key="sb_back", use_container_width=True):
            st.session_state.jira_auth_popup_actioned = False
            st.session_state.jira_user_authenticated  = False
            st.session_state.selected_helper          = None
            st.rerun()

        # ── User badge ──
        user = st.session_state.get("logged_in_user", "")
        if user:
            st.markdown(f'<div class="sb-user-badge">● {user} · Jira connected</div>', unsafe_allow_html=True)

        st.markdown('<div class="sb-section-label">Choose a Helper</div>', unsafe_allow_html=True)

        ras_sel = st.session_state.get("selected_helper") == HELPER_RAS
        tcg_sel = st.session_state.get("selected_helper") == HELPER_TCG

        if st.button("Requirement Analysis", key="nav_ras", use_container_width=True,
                     type="primary" if ras_sel else "secondary",
                     help="Refine requirements into INVEST user stories"):
            st.session_state.selected_helper     = HELPER_RAS
            st.session_state.selected_input_type = INPUT_FREE
            st.session_state.rewritten_content   = {}
            st.session_state.jira_selected       = []
            st.session_state.free_text_input     = None
            st.rerun()

        if st.button("Test Case Generator", key="nav_tcg", use_container_width=True,
                     type="primary" if tcg_sel else "secondary",
                     help="Generate Manual or BDD test cases"):
            st.session_state.selected_helper     = HELPER_TCG
            st.session_state.selected_input_type = INPUT_FREE
            st.session_state.rewritten_content   = {}
            st.session_state.jira_selected       = []
            st.session_state.free_text_input     = None
            st.rerun()

        if tcg_sel:
            with st.container(border=True):
                st.markdown('<div class="sb-section-label" style="margin-top:0">Test Case Type</div>', unsafe_allow_html=True)
                st.session_state.tcg_selected_btn = st.radio(
                    "Test Case Type", ["Manual", "Automated"], index=0,
                    key="tcg_type_radio", horizontal=True,
                    label_visibility="collapsed",
                )

        # ── Input source (only after helper selected) ──
        if st.session_state.get("selected_helper"):
            st.markdown('<div class="sb-section-label">Input Source</div>', unsafe_allow_html=True)
            inp = st.session_state.get("selected_input_type", INPUT_FREE)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Free Text", key="inp_free", use_container_width=True,
                             type="primary" if inp == INPUT_FREE else "secondary"):
                    st.session_state.selected_input_type = INPUT_FREE
                    st.session_state.free_text_input     = None
                    st.session_state.rewritten_content   = {}
                    st.rerun()
            with c2:
                if st.button("Jira Ticket", key="inp_jira", use_container_width=True,
                             type="primary" if inp == INPUT_JIRA else "secondary"):
                    st.session_state.selected_input_type = INPUT_JIRA
                    st.session_state.jira_selected       = []
                    st.session_state.rewritten_content   = {}
                    st.rerun()

        # ── Ticket picker ──
        if st.session_state.get("selected_input_type") == INPUT_JIRA:
            col_label, col_refresh = st.columns([4, 1])
            with col_label:
                st.markdown('<div class="sb-section-label" style="margin-top:6px">Select tickets:</div>', unsafe_allow_html=True)
            with col_refresh:
                if st.button("↺", key="refresh_tickets", help="Reload tickets from Jira"):
                    st.session_state.pop("jira_ids_all", None)
                    st.session_state.jira_fetch_error = None
                    st.rerun()

            if "jira_ids_all" not in st.session_state:
                with st.spinner("Loading Jira stories..."):
                    try:
                        ids = jira.get_accessible_issues(["Story"])
                        st.session_state.jira_ids_all    = ids
                        st.session_state.jira_fetch_error = None
                    except Exception as e:
                        st.session_state.jira_ids_all    = []
                        st.session_state.jira_fetch_error = str(e)

            fetch_err = st.session_state.get("jira_fetch_error")
            if fetch_err:
                st.error(f"Could not load tickets: {fetch_err}")

            all_ids = st.session_state.get("jira_ids_all", [])
            count   = st.session_state.get("jira_display_count", 200)
            to_show = all_ids[:count]

            if all_ids:
                st.caption(f"{len(all_ids)} stor{'y' if len(all_ids)==1 else 'ies'} found")
            elif not fetch_err:
                st.info("No Stories found in this Jira project. Make sure your tickets are of type **Story**.")

            selected = st.multiselect(
                "Jira Stories",
                options=to_show,
                default=[t for t in st.session_state.get("jira_selected", []) if t in to_show],
                key="jira_multiselect",
                on_change=_update_jira_selected,
                label_visibility="collapsed",
                placeholder="Type to search or pick tickets…",
            )
            if selected != st.session_state.get("jira_selected", []):
                st.session_state.jira_selected = selected
            if count < len(all_ids):
                if st.button(f"Load more ({len(all_ids) - count} remaining)", key="load_more"):
                    st.session_state.jira_display_count = count + 50
                    st.rerun()

        st.markdown('<hr style="border-color:rgba(255,255,255,0.06);margin:12px 0">', unsafe_allow_html=True)
        health_panel()
