import streamlit as st
import streamlit.components.v1 as components

def star_rating(label, key):
    st.markdown(f"#### {label}")

    components.html(f"""
    <style>
        .star-rating {{
            display: flex;
            flex-direction: row-reverse;
            justify-content: left;
            font-size: 2em;
        }}
        .star-rating input[type="radio"] {{
            display: none;
        }}
        .star-rating label {{
            color: transparent;
            text-shadow: 0 0 0 white; 
            cursor: pointer;
        }}
        .star-rating input[type="radio"]:checked + label,
        .star-rating input[type="radio"]:checked + label ~ label {{
            color: gold;
            text-shadow: none;
        }}
        .star-rating label:hover,
        .star-rating label:hover ~ label {{
            color: gold;
            text-shadow: none;
            
        }}
    </style>
    <div class="star-rating" id="{key}_container">
        <input type="radio" id="{key}_5" name="{key}" value="5"><label for="{key}_5">★</label>
        <input type="radio" id="{key}_4" name="{key}" value="4"><label for="{key}_4">★</label>
        <input type="radio" id="{key}_3" name="{key}" value="3"><label for="{key}_3">★</label>
        <input type="radio" id="{key}_2" name="{key}" value="2"><label for="{key}_2">★</label>
        <input type="radio" id="{key}_1" name="{key}" value="1"><label for="{key}_1">★</label>
    </div>

    <script>
        const container = document.getElementById("{key}_container");
        container.addEventListener('change', function(e) {{
            const selectedRating = e.target.value;
            const streamlitEvent = new Event("input", {{ bubbles: true }});
            const hiddenInput = window.parent.document.querySelector('input[data-testid="stTextInput"]');
            if (hiddenInput) {{
                hiddenInput.value = selectedRating;
                hiddenInput.dispatchEvent(streamlitEvent);
            }}
        }});
    </script>
    """, height=100)
    
    return None