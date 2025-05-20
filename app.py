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

# initialize test phases & state (only runs once)
if "phase" not in st.session_state:
    st.session_state["phase"]               = "introduction"
    st.session_state["sheet_index"]         = 0
    st.session_state["item_index"]          = 0
    st.session_state["imm_correct"]         = {}  # per-sheet immediate recall flags
    st.session_state["free_transcript"]     = []
    st.session_state["cued_responses"]      = {}

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
    if st.session_state["phase"] != "introduction":
        return

    st.header("Introduction")
    st.write(
        "You’ll learn 16 words, each tied to a unique category. "
        "I’ll read each category aloud—then you say the matching word. "
        "After that we’ll test you three ways: immediate cued recall, free recall, and cued recall."
    )
    if st.button("Begin Learning"):
        st.session_state["phase"] = "controlled"

def controlled_learning():
    if st.session_state["phase"] != "controlled":
        return

    sheet_idx = st.session_state["sheet_index"]
    sheet     = study_sheets[sheet_idx]
    cues      = list(sheet.keys())
    cue       = cues[st.session_state["item_index"]]
    target    = sheet[cue]

    st.header(f"Controlled Learning — Sheet {sheet_idx+1} of {len(study_sheets)}")

    # 1) Announce the cue
    speak_text(f"Category: {cue}. Say the word aloud, then click it below.")
    st.write(f"🔊 **Category:** {cue}")

    # 2) Show the four words as clickable options
    choice = st.radio("Click the word you just said:", list(sheet.values()), key=f"sel_{sheet_idx}_{cue}")

    # 3) When they click Confirm, record audio (for research) and check their click
    if st.button("Confirm Selection", key=f"confirm_{sheet_idx}_{cue}"):
        # record their speech for later transcription
        audio_f = record_audio(key=f"learn_{sheet_idx}_{cue}")
        if choice == target:
            st.success("✅ Correct!")
            # advance within sheet or move to next phase
            st.session_state["item_index"] += 1
            if st.session_state["item_index"] >= len(cues):
                # reset item pointer
                st.session_state["item_index"] = 0
                # go to immediate recall if that was the last sheet
                if sheet_idx + 1 >= len(study_sheets):
                    st.session_state["phase"] = "immediate"
                else:
                    # otherwise move to next sheet
                    st.session_state["sheet_index"] += 1
            st.experimental_rerun()
        else:
            st.error(f"❌ That’s not the right word. The correct answer was **{target}**. Try again.")

def immediate_cued_recall():
    if st.session_state["phase"] != "immediate":
        return

    sheet_idx = st.session_state["sheet_index"]
    sheet     = study_sheets[sheet_idx]
    flags     = st.session_state["imm_correct"].setdefault(sheet_idx, {cue: False for cue in sheet})

    for cue, word in sheet.items():
        if not flags[cue]:
            st.write(f"🔉 Cue: {cue}")
            audio_f = record_audio(key=f"imm_{sheet_idx}_{cue}")
            if audio_f:
                resp = transcribe_audio(audio_f).strip().lower()
                if resp == word.lower():
                    st.success("✅ Correct!")
                    flags[cue] = True
                else:
                    # remind per protocol:
                    speak_text(f"The {cue} was {word}. What was the {cue}?")
                    retry_f = record_audio(key=f"imm_retry_{sheet_idx}_{cue}")
                    resp2   = transcribe_audio(retry_f).strip().lower()
                    if resp2 == word.lower():
                        st.success("✅ Got it!")
                        flags[cue] = True
                    else:
                        st.error("Still not right—let’s keep going, you’ll get the next ones!")
            return  # exit so we handle ONE cue at a time

    # if we reach here, all 4 cues that sheet are correct
    # advance to next sheet or interference
    if sheet_idx + 1 < len(study_sheets):
        st.session_state["sheet_index"] += 1
        st.session_state["phase"]        = "controlled"
    else:
        st.session_state["phase"] = "interference"
    st.session_state["item_index"] = 0


def interference_phase():
    if st.session_state["phase"] != "interference":
        return

    st.header("Interference")
    st.write("Count down by 3’s from 97 for 20 seconds.")
    if st.button("Start Interference"):
        countdown_seconds(20)
        st.session_state["phase"] = "free_recall"

def free_recall_phase():
    if st.session_state["phase"] != "free_recall":
        return

    st.header("Free Recall")
    st.write("Tell me all the words you remember, in any order. You have 90 seconds.")

    # record one 90s chunk
    free_f = record_audio(key="free_recall")
    if free_f:
        txt = transcribe_audio(free_f)
        st.session_state["free_transcript"] = txt.split()
        st.write("You said:", st.session_state["free_transcript"])

    if st.button("Done Free Recall"):
        st.session_state["phase"] = "cued_recall"

def cued_recall_phase():
    if st.session_state["phase"] != "cued_recall":
        return

    st.header("Cued Recall")
    free_set = set(w.lower() for w in st.session_state["free_transcript"])
    missed   = {cue:word for cue,word in study_words.items() if word.lower() not in free_set}

    for cue, word in missed.items():
        st.write(f"🔉 Cue: {cue}")
        f = record_audio(key=f"cue_{cue}")
        if f:
            resp = transcribe_audio(f).strip().lower()
            st.session_state["cued_responses"][cue] = resp
    if st.button("See Results"):
        st.session_state["phase"] = "results"

def show_results():
    if st.session_state["phase"] != "results":
        return

    # ICR total
    icr_score = sum(
        sum(flags.values())
        for flags in st.session_state["imm_correct"].values()
    )

    # Free Recall
    free_list = st.session_state["free_transcript"]
    free_norm = {w.lower() for w in free_list}
    fr_score  = sum(1 for w in study_words.values() if w.lower() in free_norm)

    # Cued Recall & Intrusions
    missed     = {cue:word for cue,word in study_words.items() if word.lower() not in free_norm}
    cr_resp    = st.session_state["cued_responses"]
    cr_score   = 0
    intrusions = 0
    for cue, word in missed.items():
        r = cr_resp.get(cue, "").lower().strip()
        if r == word.lower():
            cr_score += 1
        elif r:
            intrusions += 1

    total = icr_score + fr_score + cr_score

    st.header("Final Score")
    st.write(f"• Immediate Cued Recall: {icr_score} / 16")
    st.write(f"• Free Recall: {fr_score} / 16")
    st.write(f"• Cued Recall: {cr_score} / {len(missed)}")
    st.write(f"• Intrusions: {intrusions}")
    st.write(f"**Overall FCSRT-IR total: {total} / 48**")

if __name__ == "__main__":
    main()
