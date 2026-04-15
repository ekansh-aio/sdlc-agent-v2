import streamlit as st
import streamlit.components.v1 as cp
from streamlit_extras.stylable_container import stylable_container
from streamlit_extras.stylable_container import stylable_container
import streamlit as st


def button_container(key, label, type):
    is_selected = st.session_state.get(f"{type}_{key}_selected", False)

    bg_color    = "#cc0000" if is_selected else "rgba(255,255,255,0.04)"
    text_color  = "#ffffff" if is_selected else "#a0a4b4"
    border      = "1px solid #cc0000" if is_selected else "1px solid rgba(204,0,0,0.38)"
    font_weight = "700" if is_selected else "500"
    shadow      = "0 3px 12px rgba(204,0,0,0.35)" if is_selected else "none"

    with stylable_container(
        key=key,
        css_styles=[
            f"""
            button {{
                border: {border};
                border-radius: 8px;
                color: {text_color};
                background: {bg_color};
                padding: 7px 16px;
                font-weight: {font_weight};
                font-size: 13px;
                margin: 1px 0;
                transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: {shadow};
                letter-spacing: 0.2px;
                width: 100%;
            }}
            """,
            """
            button:hover {
                background: #cc0000 !important;
                border: 1px solid #cc0000 !important;
                color: #ffffff !important;
                box-shadow: 0 4px 16px rgba(204,0,0,0.40) !important;
                transform: translateY(-1px);
            }
            """,
            """
            button:active {
                transform: translateY(0) !important;
                box-shadow: none !important;
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
                            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                            body {{ background: transparent; display: flex; align-items: center; }}
                            .copy-btn {{
                                display: inline-flex;
                                align-items: center;
                                gap: 6px;
                                background: rgba(255,255,255,0.05);
                                border: 1px solid rgba(204,0,0,0.50);
                                border-radius: 8px;
                                padding: 6px 14px;
                                font-size: 12.5px;
                                font-weight: 600;
                                font-family: 'Segoe UI', 'Inter', system-ui, sans-serif;
                                color: #b0b4c8;
                                cursor: pointer;
                                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                                white-space: nowrap;
                            }}
                            .copy-btn:hover {{
                                background: #cc0000;
                                border-color: #cc0000;
                                color: white;
                                box-shadow: 0 4px 14px rgba(204,0,0,0.38);
                                transform: translateY(-1px);
                            }}
                            .copy-btn:active {{
                                transform: translateY(0);
                                box-shadow: none;
                            }}
                            .copy-btn.copied {{
                                background: rgba(74,222,128,0.15);
                                border-color: rgba(74,222,128,0.40);
                                color: #4ade80;
                            }}
                        </style>
                    </head>
                    <body>
                        <button class="copy-btn" id="copyBtn" onclick="copyToClipboard()">
                            📋 Copy
                        </button>
                        <script>
                            function copyToClipboard() {{
                                const text = {escaped_response};
                                const btn = document.getElementById('copyBtn');
                                navigator.clipboard.writeText(text).then(function() {{
                                    btn.classList.add('copied');
                                    btn.innerHTML = '✅ Copied!';
                                    setTimeout(function() {{
                                        btn.classList.remove('copied');
                                        btn.innerHTML = '📋 Copy';
                                    }}, 2000);
                                }}, function(err) {{
                                    btn.innerHTML = '❌ Failed';
                                    setTimeout(function() {{
                                        btn.innerHTML = '📋 Copy';
                                    }}, 2000);
                                }});
                            }}
                        </script>
                    </body>
                    </html>
                    """, height=50)

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
