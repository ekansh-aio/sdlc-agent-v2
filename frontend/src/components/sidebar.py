import streamlit as st
from components.buttons import button_container, header_buttons
from utils.health_check import run_frontend_checks

# Status icons and colours for each check state
_STATUS_ICON  = {"ok": "✅", "warn": "⚠️", "fail": "❌"}
_STATUS_COLOR = {"ok": "green", "warn": "orange", "fail": "red"}
_CHECK_LABELS = {
    "postgresql":         "PostgreSQL (logging)",
    "jira_endpoint":      "Jira Endpoint",
    "azure_function_app": "Azure Function App",
}


def _render_system_status():
    """
    Runs health checks once per session (cached in session_state).
    Renders a collapsible status panel in the sidebar.
    Auto-expands when there is at least one warning or failure.
    """
    if "health_check_results" not in st.session_state:
        st.session_state.health_check_results = run_frontend_checks()

    report  = st.session_state.health_check_results
    overall = report["overall"]
    checks  = report["checks"]

    overall_icon  = _STATUS_ICON[overall]
    overall_color = _STATUS_COLOR[overall]
    expand_panel  = overall in ("warn", "fail")

    with st.expander(
        f"{overall_icon} System Status",
        expanded=expand_panel,
    ):
        for key, result in checks.items():
            status  = result["status"]
            icon    = _STATUS_ICON[status]
            color   = _STATUS_COLOR[status]
            label   = _CHECK_LABELS.get(key, key)
            message = result["message"]

            st.markdown(
                f'<span style="color:{color}">{icon} **{label}**</span><br>'
                f'<span style="font-size:0.82em; color:{color}">{message}</span>',
                unsafe_allow_html=True,
            )

            # Show detail lines for non-ok statuses
            if status != "ok":
                for k, v in result.get("detail", {}).items():
                    st.markdown(
                        f'<span style="font-size:0.78em; color:grey; margin-left:1.5em">'
                        f"→ **{k}**: {v}</span>",
                        unsafe_allow_html=True,
                    )

            st.markdown("<div style='margin-bottom:4px'></div>", unsafe_allow_html=True)

        if overall == "ok":
            st.markdown(
                "<span style='color:green; font-size:0.82em'>All systems ready.</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<span style='font-size:0.78em; color:grey'>"
                "Fix issues above before running agents.</span>",
                unsafe_allow_html=True,
            )

        if st.button("Re-check", key="health_recheck"):
            del st.session_state.health_check_results
            st.rerun()


def update_jira_selected():
    st.session_state.jira_selected = st.session_state.jira_multiselect

def sidebar_display(jira):
    
    st.markdown("""
        <style>
        [data-testid="stSidebar"] .custom-radio-label {
            color: white;
            font-weight: 600;
            font-size: 16px;
            display: block;
            margin-bottom: 10px;
        }

        [data-testid="stSidebar"] .stRadio div > div {
            color: white !important;
            font-weight: 500;
        }

        [data-testid="stSidebar"] .stRadio input[type="radio"] {
            accent-color: red;
        }

        [data-testid="stSidebar"] button[kind="secondary"] {
            border: 2px solid red;
            color: black !important;
            transition: all 0.3s ease;
            padding: 0.5em 1.5em;
        }
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:

        header_buttons()

        _render_system_status()

        with st.container():
            st.markdown("**Please select the QE helper**")

            if button_container("button_1", "Requirement Analysis & Standardization", "Helper"):
                st.session_state.selected_helper = "Requirement Analysis & Standardization"
                st.session_state.selected_input_type = False
                st.rerun()

            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

            if button_container("button_2", "Test Case Generator", "Helper"):
                st.session_state.selected_helper = "Test Case Generator"
                st.session_state.selected_input_type = False
                st.session_state.test_case_type = None
                st.rerun()
                

        if st.session_state.get("selected_helper") == "Test Case Generator":
            with st.container(border=True):
                st.markdown('<span class="custom-radio-label">Select Test Case Type:</span>', unsafe_allow_html=True)
                st.session_state.tcg_selected_btn = st.radio(
                    label="",
                    options=["Manual", "Automated"],
                    index=0,
                    key="test_case_type_radio",
                    horizontal=True
                )

        if st.session_state.selected_helper:
            st.markdown(""" """)
            with st.container(border=True):
                st.markdown("**Please select the input type to helper**")

                if st.session_state.jira_user_authenticated:
                    if button_container("button_4", "Free Text Requirement", "Input Type"):
                        st.session_state.selected_input_type = "Free Text Requirement"
                        st.session_state["free_text_input"] = None
                        st.rerun()

                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

                    if button_container("button_3", "Jira ID", "Input Type"):
                        st.session_state.selected_input_type = "Jira ID"
                        st.session_state.show_multiselect = True
                        st.session_state.selected_options = []
                        st.session_state.show_all_options = False
                        st.rerun()
                else:
                    if button_container("button_4", "Free Text Requirement", "Input Type"):
                        st.session_state.selected_input_type = "Free Text Requirement"
                        st.session_state["free_text_input"] = None
                        st.rerun()

                # Show Jira ID selection
                if st.session_state.selected_input_type == "Jira ID":
                    if "jira_ids_all" not in st.session_state:
                        st.session_state.jira_ids_all = jira.get_accessible_issues(['Story'])

                    if "jira_selected" not in st.session_state:
                        st.session_state.jira_selected = []

                    jira_ids_to_display = (
                        st.session_state.jira_ids_all[:st.session_state.jira_display_count]
                        if len(st.session_state.jira_ids_all) >= st.session_state.jira_display_count
                        else st.session_state.jira_ids_all
                    )

                    selected = st.multiselect(
                        "Select Jira IDs:",
                        options=jira_ids_to_display,
                        default=st.session_state.jira_selected,
                        key="jira_multiselect",
                        on_change=update_jira_selected
                    )

                    if selected != st.session_state.jira_selected:
                        st.session_state.jira_selected = selected

                    if st.session_state.jira_display_count < len(st.session_state.jira_ids_all):
                        if st.button("More..."):
                            st.session_state.jira_display_count += 5
                            st.rerun()

                    print("Selected jira", st.session_state.jira_selected)

