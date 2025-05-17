import sounddevice as sd
import soundfile as sf
from datetime import datetime
from pathlib import Path

AUDIO_DIR = Path(__file__).resolve().parent.parent / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def record_audio(duration_sec=60, sample_rate=44100):
    filename = AUDIO_DIR / f"distraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    print(f"Recording to: {filename}")
    recording = sd.rec(int(duration_sec * sample_rate), samplerate=sample_rate, channels=1)
    sd.wait()
    sf.write(filename, recording, sample_rate)
    return filename