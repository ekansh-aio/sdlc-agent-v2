import streamlit as st

def load_css(css_file_path: str):
    try:
        with open(css_file_path,"r") as f:
            css=f"<style>{f.read()}</style>"
            st.markdown(css, unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"CSS file not found: {css_file_path}")
    except Exception as e:
        st.error(f"An error occured while loading css file: {e}")