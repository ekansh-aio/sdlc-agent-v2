import streamlit as st

def emoji_rating(label="Rate this:", key="emoji_rating") -> int | None:
    st.markdown(f"**{label}**")

    emojis = {
        1: "😡",
        2: "😕",
        3: "😐",
        4: "🙂",
        5: "😍"
    }

    # Reduce spacing by customizing column width ratios
    cols = st.columns([0.8, 0.8, 0.8, 0.8, 0.8])
    selected_rating = st.session_state.get(key)

    for i, col in enumerate(cols, start=1):
        if col.button(emojis[i], key=f"{key}_{i}"):
            selected_rating = i
            st.session_state[key] = selected_rating

    return selected_rating
