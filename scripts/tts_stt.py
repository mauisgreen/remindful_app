import pyttsx3
import whisper

_model = whisper.load_model("base")    # load once

def speak_text(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

def transcribe_audio(file_path):
    # reuse pre-loaded model
    result = _model.transcribe(str(file_path))
    return result.get("text", "")
