import streamlit as st
from audiorecorder import audiorecorder
from pathlib import Path
from datetime import datetime

AUDIO_DIR = Path(__file__).resolve().parent.parent / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def record_audio(key: str):
    \"\"\"Uses a Streamlit audio recorder component to capture and save WAV data.\"\"\"
    # Display recorder UI
    wav_data = audiorecorder("▶️ Record", "⏹️ Stop", key=key)
    if wav_data:
        filename = AUDIO_DIR / f\"recording_{key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav\"
        # Write raw audio bytes to file
        with open(filename, "wb") as f:
            f.write(wav_data.tobytes())
        st.success(f\"Saved recording to {filename.name}\")
        return filename
    else:
        st.info(\"Click record to start capturing audio.\")
        return None
