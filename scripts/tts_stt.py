import whisper

def speak_text(text: str):
    """
    No-op on Streamlit Cloud (where pyttsx3/eSpeak isn’t available).
    """
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    except Exception:
        # silently skip TTS if it fails
        pass

def transcribe_audio(file_path):
    """
    Lazy-load Whisper so we don’t import torch at startup.
    """
    # note: this import only happens when you actually transcribe
    model = whisper.load_model("base")
    result = model.transcribe(str(file_path))
    return result["text"]