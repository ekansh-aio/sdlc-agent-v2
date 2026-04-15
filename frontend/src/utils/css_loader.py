import os
import streamlit as st

# static/ lives at frontend/static/
# This file is at frontend/src/utils/css_loader.py — need 3 levels up to reach frontend/
_FRONTEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_css(css_file_path: str):
    if not os.path.isabs(css_file_path):
        css_file_path = os.path.join(_FRONTEND_DIR, css_file_path)
    try:
        with open(css_file_path,"r") as f:
            css=f"<style>{f.read()}</style>"
            st.markdown(css, unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"CSS file not found: {css_file_path}")
    except Exception as e:
        st.error(f"An error occured while loading css file: {e}")