# Create a working MVP timer module with countdown handling
timer_code = """
import time
import streamlit as st

def countdown(minutes: int):
    total_seconds = minutes * 60
    for remaining in range(total_seconds, 0, -1):
        mins, secs = divmod(remaining, 60)
        timer_text = f"{mins:02}:{secs:02}"
        st.markdown(f"### Distraction timer: {timer_text}")
        time.sleep(1)
        st.experimental_rerun()  # Rerun to update timer each second (Streamlit workaround)
"""

# Write to the timer.py file
timer_path = Path("/mnt/data/remindful_app/scripts/timer.py")
timer_path.write_text(timer_code)

timer_path.name
