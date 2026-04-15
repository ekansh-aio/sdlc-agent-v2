import os
import streamlit as st

_STATIC = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "static"
)


def _get_css(filename: str) -> str:
    """Always read from disk so changes take effect without restarting the worker."""
    path = os.path.join(_STATIC, filename)
    with open(path) as f:
        return f.read()


def load_theme():
    """Inject global CSS + Google Fonts into the page (must run every rerun)."""
    # Hard-reset Streamlit's red primary color before the main stylesheet loads.
    # Streamlit injects `--primary-color` inline on :root; we override it here
    # so any button rendered before our full CSS parses already has the right color.
    st.markdown("""<style>
    :root { --primary-color: #388bfd !important; }
    button[kind="primary"], [data-testid="stBaseButton-primary"] button,
    [data-testid="stBaseButton-primary"] > button {
        background: linear-gradient(135deg,#388bfd 0%,#a371f7 100%) !important;
        border: none !important; color: #fff !important;
    }
    </style>""", unsafe_allow_html=True)
    st.markdown(
        f"<style>{_get_css('styles.css')}</style>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans'
        ':wght@400;500;600;700;800&display=swap" rel="stylesheet">',
        unsafe_allow_html=True,
    )


def load_chat_css():
    st.markdown(
        f"<style>{_get_css('agent_chat.css')}</style>",
        unsafe_allow_html=True,
    )


def landing_gradient():
    """Radial gradient blobs — apply on every screen for visual consistency."""
    st.markdown("""<style>
    .block-container {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        max-width: 100% !important;
    }
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(ellipse 55% 45% at 10% 15%, rgba(56,139,253,0.13) 0%, transparent 70%),
            radial-gradient(ellipse 45% 40% at 90% 85%, rgba(163,113,247,0.10) 0%, transparent 70%),
            #0d1117 !important;
    }
    </style>""", unsafe_allow_html=True)
