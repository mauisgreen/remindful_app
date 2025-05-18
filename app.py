import streamlit as st
from pathlib import Path
from scripts.scoring import score_responses
from scripts.timer import countdown
from scripts.audio_handler import record_audio
from scripts.tts_stt import speak_text, transcribe_audio

# Update with your full 16-item list
study_words = {
    "fruit": "apple",
    "vehicle": "truck",
    "furniture": "couch"
}

def main():
    st.title("Remindful Memory Test")
    # Initialize session state
    if "phase" not in st.session_state:
        st.session_state.phase = "study"
    if "responses_immediate" not in st.session_state:
        st.session_state.responses_immediate = {}
    if "responses_delayed" not in st.session_state:
        st.session_state.responses_delayed = {}

    if st.session_state.phase == "study":
        study_phase()
    elif st.session_state.phase == "immediate":
        immediate_recall_phase()
    elif st.session_state.phase == "distract":
        distraction_phase()
    elif st.session_state.phase == "delayed":
        delayed_recall_phase()

def study_phase():
    st.header("Study Phase")
    for cue, word in study_words.items():
        st.write(f"{cue.capitalize()} — {word}")
    if st.button("Next: Immediate Recall"):
        st.session_state.phase = "immediate"
        st.experimental_rerun()

def immediate_recall_phase():
    st.header("Immediate Cued Recall")
    for cue in study_words:
        key = f"imm_{cue}"
        st.session_state.responses_immediate[cue] = st.text_input(f"What was the {cue}?", key=key)
    if st.button("Start Distraction Task"):
        st.session_state.phase = "distract"
        st.experimental_rerun()

def distraction_phase():
    st.header("Distraction Task")
    st.write("Part 1: Name as many animals as you can in one minute.")
    st.write("Part 2: Count backwards from 100 by 3s for one minute.")
    if st.button("Start Distraction"):
        audio_file = record_audio(duration_sec=120)
        countdown(2)
        st.session_state.last_audio = str(audio_file)
        st.session_state.phase = "delayed"
        st.experimental_rerun()

def delayed_recall_phase():
    st.header("Delayed Cued Recall")
    for cue in study_words:
        key = f"del_{cue}"
        st.session_state.responses_delayed[cue] = st.text_input(f"What was the {cue}? (Delayed)", key=key)
    if st.button("See Results"):
        score_imm, details_imm = score_responses(study_words, st.session_state.responses_immediate)
        score_del, details_del = score_responses(study_words, st.session_state.responses_delayed)
        st.subheader("Results")
        st.write(f"Immediate Recall: {score_imm} / {len(study_words)}")
        st.write(f"Delayed Recall: {score_del} / {len(study_words)}")
        if "last_audio" in st.session_state:
            if st.button("Transcribe Distraction Audio"):
                transcript = transcribe_audio(Path(st.session_state.last_audio))
                st.text_area("Distraction Transcript", transcript)

if __name__ == "__main__":
    main()