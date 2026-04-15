import streamlit as st

def initialize_session_state():
    default_stats = {
        "selected_helper":          None,
        "selected_input_type":      None,
        "jira_auth_popup_actioned": False,
        "jira_user_authenticated":  False,
        "jira_display_count":       200,
        "jira_ids_max_results":     200,
        "free_text_input":          None,
        "free_text_response":       None,
        "jira_selected":            [],
        "rewritten_content":        {},
        "pushed_status":            {},
        "logged_in_user":           None,
        "invalid_len_input":        False,
        "jira_username":            None,
        "jira_password":            None,
        "show_jira_login":          False,
        "tcg_selected_btn":         "Manual",
        "previous_jira_selected":   [],
        "_prev_input_type":         None,
    }

    for key, value in default_stats.items():
        if key not in st.session_state:
            st.session_state[key] = value