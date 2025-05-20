import streamlit as st
from pathlib import Path
import json
from datetime import datetime
from scripts.scoring      import score_responses
from scripts.timer        import countdown, countdown_seconds
from scripts.audio_handler import record_audio
from scripts.tts_stt       import speak_text, transcribe_audio
from scripts.helpers      import chunk_dict

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
if "phase" not in st.session_state:
    st.session_state["phase"]               = "introduction"
    st.session_state["sheet_index"]         = 0
    st.session_state["item_index"]          = 0
    st.session_state["responses_immediate"] = {}
    st.session_state["free_transcript"]     = []
    st.session_state["responses_cued"]      = {}

def main():
    phase = st.session_state["phase"]
    if phase == "introduction":
        introduction()
    elif phase == "controlled":
        controlled_learning()
    elif phase == "immediate":
        immediate_cued_recall()
    elif phase == "interference":
        interference_phase()
    elif phase == "free_recall":
        free_recall_phase()
    elif phase == "cued_recall":
        cued_recall_phase()
    elif phase == "results":
        show_results()

def introduction():
    st.header("Introduction")
    st.write(
        "In this exercise you’ll learn 16 words, each tied     to its own category. "
        "I’ll say each category aloud; you then speak the matching word. "
        "After learning, you’ll do three recall trials."
    )
    if st.button("Begin Learning"):
        st.session_state["phase"] = "controlled"
        st.experimental_rerun()

def controlled_learning():
    if st.session_state["phase"] != "controlled":
        return

    st.header("Controlled Learning")

    idx    = st.session_state["sheet_index"]
    pos    = st.session_state["item_index"]
    sheet  = study_sheets[idx]
    cues   = list(sheet.keys())
    cue    = cues[pos]
    target = sheet[cue]

    # Speak the cue automatically
    speak_text(f"Category: {cue}. Please say the associated word.")
    st.write(f"🔊 **Category:** {cue}")

    # Record & transcribe
    audio_file = record_audio(key=f"learn_{idx}_{pos}")
    if audio_file:
        resp = transcribe_audio(audio_file).strip().lower()
        st.write(f"**You said:** {resp}")

        if resp == target.lower():
            st.success("✅ Correct!")
            # Next item or sheet
            if pos + 1 < len(cues):
                st.session_state["item_index"] += 1
            else:
                st.session_state["sheet_index"] += 1
                st.session_state["item_index"] = 0
                if st.session_state["sheet_index"] >= len(study_sheets):
                    st.session_state["phase"] = "immediate"
            st.experimental_rerun()
        else:
            st.error(f"❌ That’s not right. It was **{target}**. Let’s try again.")


def immediate_cued_recall():
    if st.session_state["phase"] != "immediate":
        return

    st.header("Immediate Cued Recall (Voice)")
    for cue in study_words:
        st.write(f"🔉 Cue: {cue}")
        audio_file = record_audio(key=f"imm_{cue}")
        if audio_file:
            resp = transcribe_audio(audio_file)
            st.session_state["responses_immediate"][cue] = resp
            st.success(f"Recorded: “{resp}”")

    if st.button("Start Distraction Task"):
        st.session_state["phase"] = "interference"
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
    # Record one chunk for free recall
    free_audio = record_audio(key="free_recall")
    if free_audio:
        # Split into individual “words” for easy matching later
        free_text = transcribe_audio(free_audio)
        st.session_state.free_transcript = free_text.split()
        st.write("You said:", st.session_state.free_transcript)
    if st.button("Done Free Recall"):
        st.session_state.phase = "cued_recall"
        st.experimental_rerun()

def cued_recall_phase():
    if st.session_state.phase != "cued_recall": return
    st.header("Cued Recall (Voice)")
    # Figure out which words they missed
    missed = {cue: word for cue, word in study_words.items()
              if word not in st.session_state.free_transcript}
    # Loop just those
    for cue, word in missed.items():
        st.write(f"🔉 Cue: {cue}")
        audio_file = record_audio(key=f"cue_{cue}")
        if audio_file:
            resp = transcribe_audio(audio_file)
            # Save for scoring
            st.session_state.responses_cued = st.session_state.get("responses_cued", {})
            st.session_state.responses_cued[cue] = resp
            st.success(f"Recorded: “{resp}”")
    if st.button("See Results"):
        st.session_state.phase = "results"
        st.experimental_rerun()

def show_results():
    if st.session_state.phase != "results":
        return

    # 1. Immediate Cued Recall (16 points)
    imm_score, _ = score_responses(
        study_words,
        st.session_state.responses_immediate
    )

    # 2. Free Recall (16 points)
    free_list = st.session_state.get("free_transcript", [])
    free_norm = {w.lower() for w in free_list}
    free_score = sum(
        1 for word in study_words.values()
        if word.lower() in free_norm
    )

    # 3. Cued Recall (16 points) for words missed in free recall
    missed = {
        cue: word
        for cue, word in study_words.items()
        if word.lower() not in free_norm
    }
    cued_resps = st.session_state.get("responses_cued", {})
    cued_score = sum(
        1
        for cue, word in missed.items()
        if cued_resps.get(cue, "").lower().strip() == word.lower()
    )

    # Total out of 48
    total = imm_score + free_score + cued_score

    st.header("Final Score")
    st.write(f"🎉 Your total Remindful score is **{total} / 48**")

if __name__ == "__main__":
    main()
