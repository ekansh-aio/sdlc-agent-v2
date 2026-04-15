import streamlit as st
import uuid

def initialize_session_state():
    default_stats = {
        "selected_helper" : None,
        "selected_input_type" : None,
        "feedback_key": str(uuid.uuid4()),
        "welcome_message": False,
        "file_upload_push_to_jira": False,
        "yes_clicked": False,
        "no_clicked": False,
        "jira_auth_popup_actioned": False,
        "jira_user_authenticated": False,
        "jira_display_count": 200,
        "jira_ids_max_results": 200,
        "free_text_input": None,
        "jira_selected": [],
        "update_approved": {},
        "rewritten_content": {},
        "pushed_status": {},
        "user_confirmed": False,
        "logged_in_user": None,
        "response_duration": 0,
        "invalid_len_input": False,
        # New authentication variables for Basic Auth
        "jira_username": None,
        "jira_password": None,
        "jira_session": None  # Keep for backward compatibility
    }

    for key, value in default_stats.items():
        if key not in st.session_state:
            st.session_state[key] = value