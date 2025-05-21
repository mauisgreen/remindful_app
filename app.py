import streamlit as st
from pathlib import Path
import json
from datetime import datetime
from scripts.scoring      import score_responses
from scripts.timer        import countdown, countdown_seconds
from scripts.audio_handler import record_audio
from scripts.tts_stt       import speak_text, transcribe_audio
from scripts.helpers      import chunk_dict
import streamlit.components.v1 as components
from rapidfuzz import fuzz

# — SETUP PATHS ————————————————————————————————————————
BASE_DIR = Path(__file__).parent
TESTS_DIR = BASE_DIR / "tests"
DATA_DIR = BASE_DIR.parent / "data"
HISTORY_PATH = DATA_DIR / "history.json"
DATA_DIR.mkdir(exist_ok=True)

# — USER IDENTIFICATION / LOGIN PAGE ——————————————————————————————————
if "user_id" not in st.session_state:
    # 1) Page title
    st.markdown("Remindful Memory Assessment")
    # 2) Intro blurb
    st.write(
        "Welcome to Remindful! \n"
        "This tool will guide you through a 16-word memory test based on a reliable protocol meant to capture early signs of memory problems.\n"
        "Please enter your unique user ID or initials below to get started."
    )
    # 3) Input box
    uid = st.text_input("User ID or initials", "")
    # 4) Halt until they type something
    if not uid:
        st.stop()
    st.session_state["user_id"] = uid

user_id = st.session_state["user_id"]


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
        "I’ll read each category aloud—then you speak the matching word. "
        "After learning, you’ll do three recall trials."
    )
    if st.button("Begin Learning"):
        st.session_state["phase"] = "controlled"

def controlled_learning():
    if st.session_state["phase"] != "controlled":
        return

    # Inject CSS for our cards
    components.html("""
      <style>
        .card {
          border: 2px solid #888;
          border-radius: 8px;
          padding: 12px;
          margin: 8px;
        }
        .card .word {
          font-size: 36px;
          text-align: center;
          margin-bottom: 8px;
        }
      </style>
    """, height=0)

    # State for this sheet/item
    idx      = st.session_state["sheet_index"]
    item_idx = st.session_state["item_index"]
    sheet    = study_sheets[idx]
    cues     = list(sheet.keys())
    cue      = cues[item_idx]
    target   = sheet[cue]

    # Header & Cue
    st.header(f"Controlled Learning — Sheet {idx+1} of {len(study_sheets)}")
    st.markdown(f"<h2 style='text-align:center;'>Cue: {cue}</h2>", unsafe_allow_html=True)

    # Browser TTS
    components.html(f"""
      <script>
        const u = new SpeechSynthesisUtterance("Cue: {cue}");
        window.speechSynthesis.speak(u);
      </script>
    """, height=0)

    # 2×2 grid of cards
    words = list(sheet.values())
    cols  = st.columns(2)
    for i, word in enumerate(words):
        with cols[i % 2]:
            # Card container
            st.markdown(
                f"<div class='card'><div class='word'>{word}</div></div>",
                unsafe_allow_html=True
            )
            # Select button
            if st.button("Select", key=f"ctrl_{idx}_{item_idx}_{i}"):
                # 1) Record + transcribe
                audio_f = record_audio(key=f"learn_{idx}_{item_idx}_{i}")
                resp    = ""
                if audio_f:
                    resp = transcribe_audio(audio_f).strip().lower()
                    st.write(f"**You said:** {resp}")

                # 2) Fuzzy‐match against the target
                score = fuzz.partial_ratio(resp, target.lower())
                if score >= 80:
                    st.success("✅ Correct!")
                    # Advance: either next item or into immediate recall
                    st.session_state["item_index"] += 1
                    if st.session_state["item_index"] >= len(cues):
                        st.session_state["phase"] = "immediate"
                    return  # Streamlit will rerun with updated state
                else:
                    st.error(f"❌ That’s not right – correct word was **{target}**.")
                    return

def immediate_cued_recall():
    if st.session_state.phase != "immediate":
        return

    idx   = st.session_state["sheet_index"]
    sheet = study_sheets[idx]
    flags = st.session_state.setdefault("imm_correct", {}).setdefault(
        idx, {cue: False for cue in sheet}
    )

    # find the next cue to test
    for cue, word in sheet.items():
        if not flags[cue]:
            st.write(f"🔉 Cue: {cue}")
            audio = record_audio(key=f"imm1_{idx}_{cue}")
            if audio:
                try:
                    resp = transcribe_audio(audio).strip().lower()
                except:
                    st.warning("Transcription failed, please try again.")
                    return
                if resp == word.lower():
                    st.success("✅ Correct!")
                    flags[cue] = True
                else:
                    # remind and retry once
                    speak_text(f"The {cue} was {word}. What was the {cue}?")
                    retry = record_audio(key=f"imm2_{idx}_{cue}")
                    if retry and transcribe_audio(retry).strip().lower() == word.lower():
                        st.success("✅ Got it on retry!")
                        flags[cue] = True
                    else:
                        st.error("Still not right—moving on.")
            return  # exit so Streamlit reruns and we handle one cue at a time

    # if we reach here, all cues on this sheet have been tested
    # advance to the *next* sheet
    st.session_state["sheet_index"] += 1
    # reset your controlled‐learning pointer
    st.session_state["item_index"] = 0

    # decide next phase
    if st.session_state["sheet_index"] < len(study_sheets):
        st.session_state.phase = "controlled"
    else:
        st.session_state.phase = "interference"



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
