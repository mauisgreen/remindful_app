import sounddevice as sd
import soundfile as sf
from datetime import datetime
from pathlib import Path

AUDIO_DIR = Path(__file__).resolve().parent.parent / "audio"

def record_audio(duration_sec=60, sample_rate=44100):
    """Records audio from default mic and saves to WAV file."""
    AUDIO_DIR.mkdir(exist_ok=True, parents=True)
    filename = AUDIO_DIR / f"distraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    recording = sd.rec(int(duration_sec * sample_rate), samplerate=sample_rate, channels=1)
    sd.wait()
    sf.write(str(filename), recording, sample_rate)
    return filename