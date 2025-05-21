import streamlit as st
from audiorecorder import audiorecorder
from pathlib import Path
from datetime import datetime
from pydub import AudioSegment

# Directory to save audio recordings
AUDIO_DIR = Path(__file__).resolve().parent.parent / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def record_audio(key: str):
    """
    Shows the in-browser recorder and saves the result to a WAV file.
    Supports raw bytes, numpy-like buffers, and pydub.AudioSegment.
    """
    wav_data = audiorecorder("▶️ Record", "⏹️ Stop", key=key)
    if not wav_data:
        return None

    filename = AUDIO_DIR / f"recording_{key}_{datetime.now():%Y%m%d_%H%M%S'}.wav"

    try:
        # 1) If it’s already bytes, just dump it
        if isinstance(wav_data, (bytes, bytearray)):
            with open(filename, "wb") as f:
                f.write(wav_data)

        # 2) If it has tobytes() (numpy arrays, array.array, etc.)
        elif hasattr(wav_data, "tobytes"):
            with open(filename, "wb") as f:
                f.write(wav_data.tobytes())

        # 3) If it’s a pydub AudioSegment
        elif isinstance(wav_data, AudioSegment):
            wav_data.export(str(filename), format="wav")

        # 4) Last‐ditch fallback: try bytes()
        else:
            with open(filename, "wb") as f:
                f.write(bytes(wav_data))

        st.success(f"Saved recording: {filename.name}")
        return filename

    except Exception as e:
        st.error(f"Couldn’t save recording: {e}")
        return None
