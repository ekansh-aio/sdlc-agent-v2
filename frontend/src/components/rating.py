import streamlit as st

def render_star_rating(label, key):
    st.write(label)

    # Initialize rating value in session_state
    if key not in st.session_state:
        st.session_state[key] = 0

    # Define HTML with inline JS to update hidden input
    rating_html = f"""
    <style>
        .stars {{
            display: inline-flex;
            cursor: pointer;
            font-size: 28px;
        }}
        .star {{
            color: #ddd;
            transition: color 0.2s;
        }}
        .star.selected {{
            color: gold;
        }}
    </style>

    <div class="stars" id="{key}_container">
        <span class="star" data-value="1">&#9733;</span>
        <span class="star" data-value="2">&#9733;</span>
        <span class="star" data-value="3">&#9733;</span>
        <span class="star" data-value="4">&#9733;</span>
        <span class="star" data-value="5">&#9733;</span>
        <input type="hidden" id="{key}_rating" name="{key}_rating" />
    </div>

    <script>
    const container = document.getElementById("{key}_container");
    const stars = container.querySelectorAll(".star");
    const ratingInput = document.getElementById("{key}_rating");

    stars.forEach((star, index) => {{
        star.addEventListener("click", () => {{
            const value = parseInt(star.getAttribute("data-value"));
            ratingInput.value = value;

            stars.forEach((s, i) => {{
                if (i < value) {{
                    s.classList.add("selected");
                }} else {{
                    s.classList.remove("selected");
                }}
            }});

            // Streamlit event trigger (optional)
            window.parent.postMessage({{ isStreamlitMessage: true, type: "streamlit:setComponentValue", value: value }}, "*");
        }});
    }});
    </script>
    """

    return rating_html
    #st.markdown(rating_html, unsafe_allow_html=True)
