import streamlit as st
from pathlib import Path
import json
from datetime import datetime
from scripts.scoring import score_responses
from scripts.timer import countdown
from scripts.audio_handler import record_audio
from scripts.tts_stt import transcribe_audio
from scripts.helpers import chunk_dict


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
    study_sheets = chunk_dict(study_words, 4)

# — MAIN APP ————————————————————————————————————————
def main():
    st.title("Remindful FCSRT-IR")
    introduction()
    controlled_learning()
    immediate_cued_recall()
    interference_phase()
    free_recall_phase()
    cued_recall_phase()
    show_results()

def introduction():
    st.header("Introduction")
    st.write(
        "In this exercise you’ll learn a list of 16 words, each one tied to a different category."
        "I’ll show you each category cue and ask you to name the matching word."
        "Once you’ve seen them all, you’ll try to recall as many words as you can in any order. You will have 3 tries."
    )
    if st.button("Begin Learning"):
        st.session_state.started = True
        st.experimental_rerun()

def controlled_learning():
    if not st.session_state.get("started"): return
    st.header("Controlled Learning")
    # We assume `study_words` is an OrderedDict or list of sheets (4 items each)
    sheet_index = st.session_state.get("sheet_index", 0)
    sheet = study_words_sheets[sheet_index]  # e.g. a list of 4 (cue, word) pairs
    correct = st.session_state.setdefault("sheet_correct", {i:False for i in range(len(sheet))})
    for i, (cue, word) in enumerate(sheet):
        st.write(f"🔍 Cue: {cue}")
        if not correct[i] and st.button(f"Respond (Sheet {sheet_index+1}, Item {i+1})", key=f"learn_{sheet_index}_{i}"):
            # record_audio & transcribe_audio could be used here if you want voice during learning
            response = word  # in FCSRT you simply point/read back, so we assume correct
            correct[i] = True
    if all(correct.values()):
        # move to next sheet
        st.session_state.sheet_index = sheet_index + 1
        if st.session_state.sheet_index >= len(study_words_sheets):
            st.session_state.phase = "immediate"
        else:
            st.session_state.sheet_correct = {i:False for i in range(len(sheet))}
        st.experimental_rerun()

def immediate_cued_recall():
    if st.session_state.phase != "immediate": return
    st.header("Immediate Cued Recall")
    misses = []
    for cue, word in study_words.items():
        st.write(f"❓ Cue: {cue}")
        if st.button(f"Answer '{cue}'", key=f"imm_{cue}"):
            audio_file = record_audio(key=f"imm_{cue}")
            resp = transcribe_audio(audio_file)
            if resp.lower().strip() != word.lower():
                # remind if wrong
                st.info(f"The {cue} was {word}. What was the {cue}?")
                misses.append((cue, word))
            else:
                st.success("Correct!")
    if not misses:
        st.session_state.phase = "interference"
        st.experimental_rerun()
    else:
        # re-test misses immediately
        for cue, word in misses:
            audio_file = record_audio(key=f"remind_{cue}")
            _ = transcribe_audio(audio_file)
        st.session_state.phase = "interference"
        st.experimental_rerun()

def interference_phase():
    if st.session_state.phase != "interference": return
    st.header("Interference (20 s)")
    st.write("Count down by 3s from 97.")
    if st.button("Start Interference"):
        countdown_seconds(20)  # you’ll need a helper that counts in seconds
        st.session_state.phase = "free_recall"
        st.experimental_rerun()

def free_recall_phase():
    if st.session_state.phase != "free_recall": return
    st.header("Free Recall (90 s)")
    transcript = st.text_area("Say all words you remember (transcription):", value="")
    if st.button("Done Free Recall"):
        st.session_state.free_transcript = transcript.split()
        st.session_state.phase = "cued_recall"
        st.experimental_rerun()

def cued_recall_phase():
    if st.session_state.phase != "cued_recall": return
    st.header("Cued Recall")
    not_recalled = [w for w in study_words.values() if w not in st.session_state.free_transcript]
    for cue, word in study_words.items():
        if word in not_recalled:
            st.write(f"❓ Cue: {cue}")
            if st.button(f"Answer '{cue}'", key=f"cue_{cue}"):
                audio_file = record_audio(key=f"cue_{cue}")
                resp = transcribe_audio(audio_file)
                _ = resp  # record under st.session_state.cued_responses[cue] = resp
    st.session_state.phase = "results"
    st.experimental_rerun()

def show_results():
    if st.session_state.phase != "results": return
    st.header("Results")
        score_imm, _ = score_responses(study_words, st.session_state.responses_immediate)
        score_del, _ = score_responses(study_words, st.session_state.responses_delayed)
        st.subheader("Results")
        st.write(f"Immediate Recall: {score_imm} / {len(study_words)}")
        st.write(f"Delayed Recall: {score_del} / {len(study_words)}")

if __name__ == "__main__":
    main()
