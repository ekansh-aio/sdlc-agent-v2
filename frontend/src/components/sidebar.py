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
    Renders a compact, dark-themed status panel in the sidebar.
    Auto-expands when there is at least one warning or failure.
    """
    if "health_check_results" not in st.session_state:
        st.session_state.health_check_results = run_frontend_checks()

    report  = st.session_state.health_check_results
    overall = report["overall"]
    checks  = report["checks"]

    expand_panel = overall in ("warn", "fail")

    # Map status to dot colour (bright enough to read on dark bg)
    _DOT_COLOR = {"ok": "#4ade80", "warn": "#fbbf24", "fail": "#f87171"}
    _LABEL_COLOR = {"ok": "#4ade80", "warn": "#fbbf24", "fail": "#f87171"}

    overall_icon = _STATUS_ICON[overall]

    with st.expander(f"{overall_icon} System Status", expanded=expand_panel):
        # Inline styles scoped to this block
        st.markdown("""
        <style>
            .sys-status-wrap { display: flex; flex-direction: column; gap: 0; }
            .sys-row {
                display: flex;
                align-items: flex-start;
                gap: 10px;
                padding: 9px 2px;
                border-bottom: 1px solid rgba(255,255,255,0.07);
            }
            .sys-row:last-child { border-bottom: none; }
            .sys-dot {
                width: 9px; height: 9px;
                border-radius: 50%;
                flex-shrink: 0;
                margin-top: 4px;
            }
            .sys-label {
                font-size: 13px;
                font-weight: 700;
                color: #dde1f0;
                line-height: 1.3;
            }
            .sys-msg {
                font-size: 11.5px;
                color: #8892a8;
                line-height: 1.45;
                margin-top: 2px;
                word-break: break-word;
            }
            .sys-footer {
                font-size: 11.5px;
                color: #6b7590;
                padding-top: 8px;
                font-style: italic;
            }
        </style>
        """, unsafe_allow_html=True)

        rows_html = '<div class="sys-status-wrap">'
        for key, result in checks.items():
            status  = result["status"]
            label   = _CHECK_LABELS.get(key, key)
            message = result["message"]
            dot_color = _DOT_COLOR[status]
            glow = f"0 0 6px {dot_color}90"
            rows_html += f"""
            <div class="sys-row">
                <span class="sys-dot" style="background:{dot_color}; box-shadow:{glow};"></span>
                <div style="flex:1; min-width:0;">
                    <div class="sys-label">{label}</div>
                    <div class="sys-msg">{message}</div>
                </div>
            </div>"""
        rows_html += "</div>"

        if overall == "ok":
            rows_html += '<div class="sys-footer">All systems operational.</div>'
        else:
            rows_html += '<div class="sys-footer">Resolve issues before running agents.</div>'

        st.markdown(rows_html, unsafe_allow_html=True)

        if st.button("↻  Re-check", key="health_recheck"):
            del st.session_state.health_check_results
            st.rerun()


def update_jira_selected():
    st.session_state.jira_selected = st.session_state.jira_multiselect

def sidebar_display(jira):
    
    st.markdown("""
        <style>
        /* ---- Sidebar scoped overrides ---- */
        [data-testid="stSidebar"] .custom-radio-label {
            color: #c8cce0;
            font-weight: 700;
            font-size: 12px;
            display: block;
            margin-bottom: 10px;
            letter-spacing: 1px;
            text-transform: uppercase;
        }
        [data-testid="stSidebar"] .stRadio > div > label {
            color: #c8cce0 !important;
            font-size: 13px !important;
        }
        [data-testid="stSidebar"] .stRadio input[type="radio"] {
            accent-color: #cc0000;
        }
        /* Home / Reset button row */
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] [data-testid="stBaseButton-secondary"] button {
            font-size: 12.5px !important;
            padding: 5px 12px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:

        header_buttons()

        _render_system_status()

        with st.container():
            st.markdown("""
            <div style="font-size:11px; font-weight:700; letter-spacing:1.2px;
                        color:#8892a8; text-transform:uppercase; padding:4px 0 8px 2px;">
                Select Helper
            </div>
            """, unsafe_allow_html=True)

            if button_container("button_1", "Requirement Analysis & Standardization", "Helper"):
                st.session_state.selected_helper = "Requirement Analysis & Standardization"
                st.session_state.selected_input_type = False
                st.rerun()

            st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)

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
            st.markdown("<div style='margin-top:6px'></div>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("""
                <div style="font-size:11px; font-weight:700; letter-spacing:1.2px;
                            color:#8892a8; text-transform:uppercase; padding:2px 0 8px 2px;">
                    Input Type
                </div>
                """, unsafe_allow_html=True)

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

