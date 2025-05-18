import streamlit as st
from pathlib import Path
import json
from datetime import datetime
from scripts.scoring import score_responses
from scripts.timer import countdown
from scripts.audio_handler import record_audio
from scripts.tts_stt import transcribe_audio

# — SETUP PATHS ————————————————————————————————————————
BASE_DIR = Path(__file__).parent
TESTS_DIR = BASE_DIR / "tests"
DATA_DIR = BASE_DIR.parent / "data"
HISTORY_PATH = DATA_DIR / "history.json"
DATA_DIR.mkdir(exist_ok=True)

# — USER IDENTIFICATION ——————————————————————————————————
if "user_id" not in st.session_state:
    uid = st.text_input("Enter your User ID or initials", "")
    if not uid:
        st.stop()
    st.session_state.user_id = uid

user_id = st.session_state.user_id

# — LOAD VERSIONS & HISTORY —————————————————————————————
versions = sorted(p.stem for p in TESTS_DIR.glob("*.json"))
history = {}
if HISTORY_PATH.exists():
    try:
        history = json.loads(HISTORY_PATH.read_text())
    except json.JSONDecodeError:
        history = {}

user_history = history.get(user_id, {})

# — PICK NEXT VERSION ————————————————————————————————————
epoch = datetime.fromisoformat("1970-01-01T00:00:00")
version_dates = {}
for v in versions:
    ts = user_history.get(v, "1970-01-01T00:00:00")
    version_dates[v] = datetime.fromisoformat(ts)
selected_version = min(version_dates, key=version_dates.get)

# — LOAD STUDY WORDS ————————————————————————————————————
with open(TESTS_DIR / f"{selected_version}.json") as f:
    study_words = json.load(f)

# — MAIN APP ————————————————————————————————————————
def main():
    st.title("Remindful Memory Test")
    st.write(f"**Test Version:** {selected_version}")

    # initialize session state
    if "phase" not in st.session_state:
        st.session_state.phase = "study"
    if "responses_immediate" not in st.session_state:
        st.session_state.responses_immediate = {}
    if "responses_delayed" not in st.session_state:
        st.session_state.responses_delayed = {}

    # phase routing
    phase = st.session_state.phase
    if phase == "study":
        study_phase()
    elif phase == "immediate":
        immediate_recall_phase()
    elif phase == "distract":
        distraction_phase()
    elif phase == "delayed":
        delayed_recall_phase()

def study_phase():
    st.header("Study Phase")
    for cue, word in study_words.items():
        st.write(f"{cue} — {word}")
    if st.button("Next: Immediate Recall"):
        st.session_state.phase = "immediate"
        st.experimental_rerun()

def immediate_recall_phase():
    st.header("Immediate Cued Recall (Voice)")
    for cue in study_words:
        st.write(f"🔉 Cue: {cue}")
        if st.button(f"Record Answer for '{cue}'", key=f"rec_im_{cue}"):
            audio_file = record_audio(duration_sec=10)
            response = transcribe_audio(audio_file)
            st.session_state.responses_immediate[cue] = response
            st.success(f"Recorded: “{response}”")
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
    st.header("Delayed Cued Recall (Voice)")
    for cue in study_words:
        st.write(f"🔉 Cue: {cue}")
        if st.button(f"Record Answer for '{cue}'", key=f"rec_del_{cue}"):
            audio_file = record_audio(duration_sec=10)
            response = transcribe_audio(audio_file)
            st.session_state.responses_delayed[cue] = response
            st.success(f"Recorded: “{response}”")
    if st.button("See Results"):
        score_imm, _ = score_responses(study_words, st.session_state.responses_immediate)
        score_del, _ = score_responses(study_words, st.session_state.responses_delayed)
        st.subheader("Results")
        st.write(f"Immediate Recall: {score_imm} / {len(study_words)}")
        st.write(f"Delayed Recall: {score_del} / {len(study_words)}")
        # update history
        now = datetime.now().isoformat()
        history.setdefault(user_id, {})[selected_version] = now
        HISTORY_PATH.write_text(json.dumps(history, indent=2))
        # optional transcription of distraction audio
        if "last_audio" in st.session_state and st.button("Transcribe Distraction Audio"):
            transcript = transcribe_audio(Path(st.session_state.last_audio))
            st.text_area("Distraction Transcript", transcript, height=200)

if __name__ == "__main__":
    main()
