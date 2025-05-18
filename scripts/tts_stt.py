import pyttsx3
import whisper

def speak_text(text):
    """Converts text to speech."""
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

def transcribe_audio(file_path):
    """Transcribes audio file to text using Whisper."""
    model = whisper.load_model("base")
    result = model.transcribe(str(file_path))
    return result.get("text", "")