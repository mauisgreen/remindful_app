import time
import streamlit as st

def countdown(minutes: int):
    """Displays a countdown timer in Streamlit for the given number of minutes."""
    placeholder = st.empty()
    total_seconds = minutes * 60
    for remaining in range(total_seconds, 0, -1):
        mins, secs = divmod(remaining, 60)
        placeholder.markdown(f"### Distraction timer: {mins:02}:{secs:02}")
        time.sleep(1)
    placeholder.empty()

def countdown_seconds(seconds: int):
    """Displays a countdown timer in Streamlit for the given number of seconds."""
    placeholder = st.empty()
    for remaining in range(seconds, 0, -1):
        placeholder.markdown(f"### Interference countdown: {remaining} seconds remaining")
        time.sleep(1)
    placeholder.empty()
