import streamlit as st
from audiorecorder import audiorecorder
from pathlib import Path
from datetime import datetime

# Directory to save audio recordings
AUDIO_DIR = Path(__file__).resolve().parent.parent / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def record_audio(key: str):
    \"""
    Uses a Streamlit audio recorder component to capture and save WAV data.
    Returns the path to the saved .wav file, or None if no recording.
    \"""
    wav_data = audiorecorder("▶️ Record", "⏹️ Stop", key=key)
    if wav_data:
        # Build filename
        filename = AUDIO_DIR / f"recording_{key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        # Determine how to write bytes
        with open(filename, "wb") as f:
            # If wav_data is bytes-like, write directly
            try:
                f.write(wav_data)
            except TypeError:
                # Otherwise, convert to bytes
                f.write(wav_data.tobytes())
        st.success(f"Saved recording as {filename.name}")
        return filename
    return None
"""

path = Path("/mnt/data/remindful_app/scripts/audio_handler.py")
path.write_text(audio_handler_code.strip())

path
