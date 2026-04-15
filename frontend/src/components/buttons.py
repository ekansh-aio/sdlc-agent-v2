import streamlit as st
import streamlit.components.v1 as cp
from streamlit_extras.stylable_container import stylable_container
from streamlit_extras.stylable_container import stylable_container
import streamlit as st


def button_container(key, label, type):
    is_selected = st.session_state.get(f"{type}_{key}_selected", False)

    bg_color = "rgb(240, 160, 160)" if is_selected else "white"
    text_color = "white" if is_selected else "black"
    border_width = ".3em" if is_selected else ".1em"
    font_weight = "bold" if is_selected else "normal"

    with stylable_container(
        key=key,
        css_styles=[
            f"""
            button {{
                border: solid {border_width} red;
                border-radius: 10px;
                color: {text_color};
                background-color: {bg_color};
                padding: 5px 15px;
                font-weight: {font_weight};
                margin: -2px 0;
                transition: all 0.3s ease-in-out;
            }}
            """,
            """
            button:hover {
                background-color: white;
                border: solid .2em red;
                color: black;
                transform: scale(1.02);
            }
            """
        ],
    ):
        if st.button(label, use_container_width=True):
            # Clear previous selection for this type
            for k in list(st.session_state.keys()):
                if k.endswith("_selected") and k.startswith(f"{type}_"):
                    st.session_state[k] = False

            if type == "Helper":
                st.session_state["selected_input_type"] = None
                for k in list(st.session_state.keys()):
                    if k.endswith("_selected") and k.startswith("Input Type_"):
                        st.session_state[k] = False
                st.session_state["free_text_input"] = None
                st.session_state["jira_selected"] = []
                st.session_state["rewritten_content"] = {}
                st.session_state["pushed_status"] = {}

            st.session_state[f"{type}_{key}_selected"] = True
            st.session_state[type] = label
            return True


# Uncomment this and comment the above block, if you do not want the buttons highlighted on click

# def button_container(key, label, type):
#     is_selected = st.session_state.get(f"{type}_{key}_selected", False)
#     with stylable_container(
#             key=key,
#             css_styles=[
#                 f"""
#                 button{{
#                     border: { 'solid .3em red' if is_selected else 'solid .1em red'};
#                     border-radius: 10px;
#                     color: {'red' if is_selected else 'black' };
#                     background-color: 'white';
#                     padding: 5px 15px;
#                     font-weight: {'bold' if is_selected else 'normal'};
#                     margin: -2px 0;
#                 }}
#                 """,
#                 f"""
#                 button:hover {{
#                     background-color: white;    
#                     border: solid .2em red;
#                     border-radius: 10px;
#                     color: black;
#                 }}
#                 """,
#             ],
#     ):
#         if st.button(label, use_container_width=True):
#             for k in st.session_state.keys():
#                 if k.endswith(f"_selected") and k.startswith(f"{type}_"):
#                     st.session_state[k] = False
            
#             #clear input type and related state when switching helpers
#             if type == "Helper":
#                 st.session_state["selected_input_type"] = None
#                 for k in st.session_state.keys():
#                     if k.endswith("_selected") and k.startswith("Input Type_"):
#                         st.session_state[k] = False
#                 st.session_state["free_text_input"] = None
#                 st.session_state["jira_selected"] = []
#                 st.session_state["rewritten_content"] = {}
#                 st.session_state["pushed_status"] = {}

#             st.session_state[f'{type}_{key}_selected'] = True
#             st.session_state[type] = label
#             return True
        
def clipboard_button(escaped_response):
    return cp.html(f"""
                    <html>
                    <head>
                        <style>
                            .st-button-like {{
                                background-color: rgb(247, 247, 247);
                                border: 1px solid #ddd;
                                border-radius: 10px 10px 10px 10px;
                                padding: 0.65rem 0.8rem;
                                font-size: 0.85rem;
                                font-family: "Source Sans Pro", sans-serif;
                                cursor: pointer;
                                box-shadow: rgba(0, 0, 0, 0.05) 0px 1px 3px;
                                transition: background-color 0.2s ease;
                                margin-top: -15px;
                                margin-left: -10px;                                        
                            }}
                            .st-button-like:hover {{
                                border: 1px solid #ff4d4f;
                                color: #ff4d4f;
                            }}                                                                                        
                        </style>
                                                                
                    </head>
                    <body>
                        <button class="st-button-like" onclick="copyToClipboard()">📋 Copy Response</button>
                        <script>
                            function copyToClipboard() {{
                                const text = {escaped_response};
                                navigator.clipboard.writeText(text).then(function() {{
                                    alert("Copied to clipboard!");
                                }}, function(err) {{
                                    alert("Failed to copy text.");
                                    console.error(err);
                                }});
                            }}
                        </script>
                    </body>
                    </html>
                    """, height=150)

def reset_app_state(include_auth=False):
    st.session_state.selected_helper = None
    st.session_state.selected_input_type = None
    st.session_state.welcome_message = False
    st.session_state.jira_selected = []
    st.session_state.free_text_input = None
    st.session_state.previous_input_type = None

    for key in list(st.session_state.keys()):
        if key.endswith("_selected"):
            del st.session_state[key]

    if include_auth:
        st.session_state.jira_auth_popup_actioned = False

    st.rerun()

def header_buttons():
    col1, col2 = st.columns([0.9, 1.7])

    with col1:
        if st.button("🏠Home", key="home_btn"):
            reset_app_state(include_auth=True)  # ← This now resets auth too

    with col2:
        if st.button("🔄Reset", key="reset_btn"):
            reset_app_state()
