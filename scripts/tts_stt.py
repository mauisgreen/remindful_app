
import pyttsx3

def speak_text(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

# Placeholder for STT (for future use with Whisper or Vosk)
def transcribe_audio(file_path):
    return "Transcription placeholder (to be implemented asynchronously)"
