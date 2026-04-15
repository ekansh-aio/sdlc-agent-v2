import streamlit as st
import json
import time
import requests
from components.file_uploader import upload_file_to_azure_blob

@st.dialog("Agent Conversation")
def chat_dialog(chat_history):
    st.markdown('<div class="chat-dialog">', unsafe_allow_html=True)
    try:    
        for message in chat_history:
            content = message.get("content")
            if not content:
                continue  # Skip empty messages

            role = message.get("role", "")
            source = message.get("source", "Unknown")

            # Determine sender name and style
            name = role if role else source if source else "Unknown"
            is_user = name.lower() == "user"
            emoji = "🧑" if is_user else "🤖"
            bubble_class = "user-bubble" if is_user else "agent-bubble"
            name_label = f"{emoji} {name}"

            # Simulate typing delay
            with st.spinner(f"{name_label} is typing..."):
                time.sleep(0.2)

            # Display chat message with style
            bubble_html = f"""
            <div class="chat-container">
                <div class="name-label">{name_label}</div>
                <div class="chat-bubble {bubble_class}">{content}</div>
            </div>
            """
            st.markdown(bubble_html, unsafe_allow_html=True)

    except Exception as e:
        st.warning(f"⚠️ Error getting agent conversation.")

    st.markdown('</div>', unsafe_allow_html=True)

@st.dialog("Please Provide Jira Credentials")
def type_user_password():
    st.text_input("Jira Username", type="default", key="user")
    st.text_input("Password", type="password", key="password")
    if st.button("**Submit**"):
        if st.session_state.user and st.session_state.password:
            st.session_state.jira_auth_popup_actioned = True
            st.session_state.jira_user_authenticated = True
        else:
            st.error("Please enter your credentials.")

    

#@st.dialog("Please authenticate to work with Jira")
def jira_auth_confirm(jira, JIRA_ENDPOINT):
    # Initialize session state flags
    if "show_jira_login" not in st.session_state:
        st.session_state.show_jira_login = False
    if "jira_user_authenticated" not in st.session_state:
        st.session_state.jira_user_authenticated = False
    if "jira_auth_popup_actioned" not in st.session_state:
        st.session_state.jira_auth_popup_actioned = False

    st.markdown("""
    <style>
        /* ---- Dark auth page ---- */
        body, .stApp, [data-testid="stAppViewContainer"] {
            background-color: #0d0e10 !important;
        }
        .auth-hero {
            background: #17181c;
            border: 1px solid rgba(255,255,255,0.07);
            border-top: 3px solid #cc0000;
            border-radius: 18px;
            padding: 40px 36px 32px;
            text-align: center;
            box-shadow: 0 8px 40px rgba(0,0,0,0.55);
            margin-bottom: 8px;
        }
        .auth-hero-icon {
            width: 60px; height: 60px; border-radius: 50%;
            background: rgba(204,0,0,0.12);
            border: 1.5px solid rgba(204,0,0,0.35);
            display: inline-flex; align-items: center; justify-content: center;
            font-size: 26px; margin-bottom: 18px;
        }
        .auth-hero h2 {
            color: #f0f1f5;
            font-size: 22px;
            font-weight: 700;
            margin: 0 0 8px 0;
            letter-spacing: 0.3px;
        }
        .auth-hero p {
            color: #6b7090;
            font-size: 13.5px;
            margin: 0;
            line-height: 1.6;
        }
        .auth-divider {
            border: none;
            border-top: 1px solid rgba(255,255,255,0.07);
            margin: 18px 0;
        }
        .auth-form-card {
            background: #1f2026;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px;
            padding: 22px 24px 18px;
            margin-top: 10px;
        }
        /* Override Streamlit input fields inside auth card */
        .auth-form-card input {
            background: #26272d !important;
            color: #f0f1f5 !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
            border-radius: 8px !important;
        }
        .auth-form-card label { color: #9b9caa !important; font-size: 13px !important; }
        div[data-testid="stBaseButton-secondary"] button {
            border-radius: 9px !important;
            font-weight: 600 !important;
            transition: all 0.22s ease !important;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="auth-hero">
        <div class="auth-hero-icon">🤖</div>
        <h2>AI Helpers for <span style="color:#cc0000;">Quality Engineering</span></h2>
        <p>Intelligent automation for your QE workflows — powered by AI agents</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr class='auth-divider'>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 4, 1])

    with col2:
        left_btn, right_btn = st.columns(2)

        with left_btn:
            if st.button("Continue without Jira", use_container_width=True):
                st.session_state.jira_user_authenticated = False
                st.session_state.jira_auth_popup_actioned = True
                st.session_state.show_jira_login = False
                st.rerun()

        with right_btn:
            if st.button("🔐 Connect to Jira", use_container_width=True):
                st.session_state.show_jira_login = True

    # Show input fields only if Authenticate was clicked
    if st.session_state.show_jira_login:
        with col2:
            st.markdown("<div class='auth-form-card'>", unsafe_allow_html=True)
            user = st.text_input("Jira Username", key="jira_user_input", placeholder="Enter your Jira username")
            password = st.text_input("Password", type="password", key="jira_pass_input", placeholder="Enter your password")

            if st.button("Connect to Jira", use_container_width=True):
                if user and password:
                    jira.set_credentials(user, password)
                    try:
                        if not jira.authenticate_user():
                            st.session_state.jira_user_authenticated = False
                            st.session_state.jira_auth_popup_actioned = False
                            st.error("❌ Invalid credentials. Please try again.")
                        else:
                            st.session_state.jira_username = user.strip()
                            st.session_state.jira_password = password
                            st.session_state.logged_in_user = user.strip()
                            st.session_state.jira_user_authenticated = True
                            st.session_state.jira_auth_popup_actioned = True
                            st.success("✅ Connected successfully!")
                            print("Jira Basic Auth configured for user: ", user.strip())
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Authentication failed: {str(e)}")
                else:
                    st.warning("Please enter both username and password.")
            st.markdown("</div>", unsafe_allow_html=True)

    # Admin Panel To upload File in Azure Blob Storage                 
    #st.markdown("""------ """)
    #st.markdown("""
    #<style>
    #    .admin-panel {
    #        font-size: 32px;
    #        color: white;
    #        background-color: white;
    #        padding: 5px 10px;
    #        border-radius: 10px;
    #        text-align: center;
    #    }
    #    .center-button {
    #        display: flex;
    #        justify-content: center;
    #    }
    #    .center-button button {
    #        width: 100%;
    #        max-width: 200px;
    #    }
    #</style>
    #        """, unsafe_allow_html=True)
    #st.markdown("<h5 class='admin-panel' style='color: Black;'>Admin Panel</h5>", unsafe_allow_html=True)
    
    

    #if st.button("Go to File Uploader"):
    #    try:
    #        st.session_state.jira_user_authenticated = False
    #        st.session_state.jira_auth_popup_actioned = False
    #        st.session_state.show_jira_login = False
    #        st.session_state.file_uploader = True

    #        response = upload_file_to_azure_blob()
    #        st.markdown(f"File uploaded successfully: {response}")
    #    except Exception as e:
    #        st.error(f"Error: {str(e)}")
    #st.markdown("""------ """)



@st.dialog("Fill Survey Form")
def survey():
    st.write(f"Please provide feedback about what did you like about the Helper and what can be improved.")
    input = st.text_input("Input...")
    if st.button("Submit"):
        st.session_state.survey_form = {"input": input}

        #save the input as JSON
        with open("survey_form.json", "w") as f:
            st.info("Feedback submitted successfully!")
            json.dump(st.session_sate.survey_form, f)
        
        st.rerun()

@st.dialog("User Confirmation")        
def user_confirm():
    st.write(f"Are you sure you want to push the data to Jira?")
    col = st.columns(2)
    st.session_state.yes_clicked = False
    st.session_state.no_clicked = False

    with col[0]:
        if st.button("Yes", disabled=st.session_state.no_clicked):
            st.session_state.yes_clicked = True
            st.session_state.no_clicked = False
            st.success("Data pushed to Jira successfully!")
            time.sleep(2)
            st.rerun()

    with col[1]:
        if st.button("No", disabled=st.session_state.yes_clicked):
            st.session_state.no_clicked = True
            st.session_state.yes_clicked = False
            st.warning("Data push to Jira cancelled.")
            time.sleep(2)
            st.rerun()


