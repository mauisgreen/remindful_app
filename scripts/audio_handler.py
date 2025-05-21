import streamlit as st
from audiorecorder import audiorecorder
from pathlib import Path
from datetime import datetime

# Directory to save audio recordings
AUDIO_DIR = Path(__file__).resolve().parent.parent / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def record_audio(key: str):
    """
    Uses a Streamlit audio recorder component to capture and save WAV data.
    Returns the path to the saved .wav file, or None if no recording.
    """
    wav_data = audiorecorder("▶️ Record", "⏹️ Stop", key=key)
    if wav_data:
        filename = AUDIO_DIR / f"recording_{key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        with open(filename, "wb") as f:
            # If wav_data is already bytes, write directly
            if isinstance(wav_data, (bytes, bytearray)):
                f.write(wav_data)
            else:
                # Otherwise, convert to bytes
                f.write(wav_data.tobytes())
        st.success(f"Saved recording as {filename.name}")
        return filename
    return None
