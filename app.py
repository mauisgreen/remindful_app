
import streamlit as st
from scripts import scoring, timer, audio_handler, tts_stt

# Sample study words
study_words = {
    "fruit": "apple",
    "vehicle": "truck",
    "furniture": "couch"
}

st.title("Remindful Memory Test")

# --- Study Phase ---
if "phase" not in st.session_state:
    st.session_state.phase = "study"
    st.session_state.responses_immediate = {}
    st.session_state.responses_delayed = {}

if st.session_state.phase == "study":
    st.header("Study Phase")
    for cue, word in study_words.items():
        st.write(f"{cue.capitalize()} — {word}")
    if st.button("Next: Immediate Recall"):
        st.session_state.phase = "immediate"

# --- Immediate Recall Phase ---
elif st.session_state.phase == "immediate":
    st.header("Immediate Cued Recall")
    for cue in study_words.keys():
        response = st.text_input(f"What was the {cue}?", key=f"imm_{cue}")
        st.session_state.responses_immediate[cue] = response
    if st.button("Start Distraction Task"):
        st.session_state.phase = "distract"

# --- Distraction Phase ---
elif st.session_state.phase == "distract":
    st.header("Distraction Task")
    st.write("Part 1: Name as many animals as you can.")
    st.write("Part 2: Count backwards from 100 by 3s.")
    if st.button("Start Recording"):
        audio_handler.record_audio(duration_sec=120)
        st.success("Recording complete.")
    if st.button("Start Timer"):
        timer.countdown(2)
    if st.button("Next: Delayed Recall"):
        st.session_state.phase = "delayed"

# --- Delayed Recall Phase ---
elif st.session_state.phase == "delayed":
    st.header("Delayed Cued Recall")
    for cue in study_words.keys():
        response = st.text_input(f"(Delayed) What was the {cue}?", key=f"del_{cue}")
        st.session_state.responses_delayed[cue] = response
    if st.button("See Results"):
        score_imm, detail_imm = scoring.score_responses(study_words, st.session_state.responses_immediate)
        score_del, detail_del = scoring.score_responses(study_words, st.session_state.responses_delayed)
        st.subheader("Results")
        st.write(f"Immediate Recall Score: {score_imm} / {len(study_words)}")
        st.write(f"Delayed Recall Score: {score_del} / {len(study_words)}")
