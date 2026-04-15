import streamlit as st
from components.dialogs import jira_auth_confirm


def jira_auth( jira,JIRA_ENDPOINT):
    
        if not st.session_state.jira_auth_popup_actioned:
            st.markdown(
        """
    <style>
    div[aria-label="dialog"] > button[aria-label="Close"] {
                    display: none;
                }
    </style>
    """,
        unsafe_allow_html=True,
    )
            jira_auth_confirm(jira, JIRA_ENDPOINT)