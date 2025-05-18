import time
import streamlit as st

def countdown(minutes: int):
    """Displays a countdown timer in Streamlit."""
    placeholder = st.empty()
    total_seconds = minutes * 60
    for remaining in range(total_seconds, 0, -1):
        mins, secs = divmod(remaining, 60)
        placeholder.markdown(f"### Distraction timer: {mins:02}:{secs:02}")
        time.sleep(1)
    placeholder.empty()