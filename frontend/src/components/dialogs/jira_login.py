import streamlit as st


@st.dialog("Connect to Jira")
def jira_login_dialog(jira):
    st.markdown("""
    <p style="color:#8b949e;font-size:13px;margin:0 0 16px;">
        Enter your Jira credentials to unlock ticket-based workflows and push to Jira.
    </p>
    """, unsafe_allow_html=True)

    user     = st.text_input("Username", key="jira_user_input",  placeholder="your-username")
    password = st.text_input("Password", type="password", key="jira_pass_input", placeholder="••••••••")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Sign in", use_container_width=True, type="primary", key="jira_signin"):
            if not user or not password:
                st.warning("Enter both username and password.")
                return
            jira.set_credentials(user, password)
            try:
                if jira.authenticate_user():
                    st.session_state.jira_username            = user.strip()
                    st.session_state.jira_password            = password
                    st.session_state.logged_in_user           = user.strip()
                    st.session_state.jira_user_authenticated  = True
                    st.session_state.jira_auth_popup_actioned = True
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
            except Exception as e:
                st.error(f"Authentication failed: {e}")
    with col2:
        if st.button("Cancel", use_container_width=True, key="jira_cancel"):
            st.session_state.show_jira_login = False
            st.rerun()
