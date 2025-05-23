import streamlit as st
from audiorecorder import audiorecorder
from pathlib import Path
from datetime import datetime
from pydub import AudioSegment

AUDIO_DIR = Path(__file__).resolve().parent.parent / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def record_audio(key: str,
                 start_label: str = "▶️ Record",
                 stop_label : str = "⏹️ Stop"):
    """
    Shows an in-browser recorder, streams status to the user,
    and returns the saved WAV file path (or None).
    """
    status = st.empty()
    wav_data = audiorecorder(start_label, stop_label, key=key)

    if not wav_data:
        status.info("Click ▶️ Record, then ⏹️ Stop when done.")
        return None

    with status.container():
        st.spinner("Processing your recording…")

    ...

    filename = AUDIO_DIR / f"recording_{key}_{datetime.now():%Y%m%d_%H%M%S}.wav"

    try:
        # Bytes-like ⇒ save directly
        if isinstance(wav_data, (bytes, bytearray)):
            filename.write_bytes(wav_data)

        # numpy / array ⇒ use tobytes()
        elif hasattr(wav_data, "tobytes"):
            filename.write_bytes(wav_data.tobytes())

        # pydub.AudioSegment ⇒ export
        elif isinstance(wav_data, AudioSegment):
            wav_data.export(str(filename), format="wav")

        # Fallback
        else:
            filename.write_bytes(bytes(wav_data))

        # 5️⃣  Success cue
        status.success("✅ Recording saved")
        return filename

    except Exception as e:
        status.error(f"❌ Couldn’t save recording: {e}")
        return None
