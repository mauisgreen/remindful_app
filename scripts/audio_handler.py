import streamlit as st
from audiorecorder import audiorecorder
from pathlib import Path
from datetime import datetime

# Ensure the audio folder exists
AUDIO_DIR = Path(__file__).resolve().parent.parent / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def record_audio(key: str):
    """
    Uses a Streamlit audio recorder component to capture and save WAV data.
    """
    # show the recorder widget
    wav_data = audiorecorder("▶️ Record", "⏹️ Stop", key=key)
    if wav_data:
        filename = AUDIO_DIR / f"recording_{key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        with open(filename, "wb") as f:
            f.write(wav_data.tobytes())
        st.success(f"Saved recording as {filename.name}")
        return filename
    return None
