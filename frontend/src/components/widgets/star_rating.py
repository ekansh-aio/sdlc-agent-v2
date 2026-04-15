import streamlit as st
import streamlit.components.v1 as components


def star_rating(label: str, key: str):
    st.markdown(
        f'<div style="font-size:12px;color:#6e7681;font-weight:500;margin-bottom:2px;">{label}</div>',
        unsafe_allow_html=True,
    )
    components.html(f"""
    <style>
        .star-rating {{ display:flex;flex-direction:row-reverse;justify-content:left;font-size:1.8em; }}
        .star-rating input[type="radio"] {{ display:none; }}
        .star-rating label {{ color:#30363d;cursor:pointer;transition:color .15s ease; }}
        .star-rating input[type="radio"]:checked + label,
        .star-rating input[type="radio"]:checked + label ~ label {{ color:#388bfd; }}
        .star-rating label:hover,
        .star-rating label:hover ~ label {{ color:#58a6ff; }}
    </style>
    <div class="star-rating" id="{key}_container">
        <input type="radio" id="{key}_5" name="{key}" value="5"><label for="{key}_5">★</label>
        <input type="radio" id="{key}_4" name="{key}" value="4"><label for="{key}_4">★</label>
        <input type="radio" id="{key}_3" name="{key}" value="3"><label for="{key}_3">★</label>
        <input type="radio" id="{key}_2" name="{key}" value="2"><label for="{key}_2">★</label>
        <input type="radio" id="{key}_1" name="{key}" value="1"><label for="{key}_1">★</label>
    </div>
    """, height=50)
