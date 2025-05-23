import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
import json
from datetime import datetime, timedelta
import random
from scripts.scoring       import score_responses
from scripts.timer         import countdown, countdown_seconds
from scripts.audio_handler import record_audio
from scripts.tts_stt        import speak_text, transcribe_audio
from scripts.helpers       import chunk_dict
import time

def show_progress():
    phase_order = ["demographics", "instructions", "controlled", "immediate",
                   "interference", "free_recall", "cued_recall", "results"]
    current = phase_order.index(st.session_state["phase"])
    st.progress(current / (len(phase_order) - 1))

def inject_big_button_css():
    st.markdown(
        """
        <style>
        button[kind="primary"]  {font-size: 24px !important; padding: 14px 24px;}
        button[kind="secondary"]{font-size: 22px !important; padding: 12px 22px;}
        </style>
        """,
        unsafe_allow_html=True,
    )

inject_big_button_css()
# — SETUP PATHS ————————————————————————————————————————
BASE_DIR     = Path(__file__).parent
TESTS_DIR    = BASE_DIR / "tests"
DATA_DIR     = BASE_DIR.parent / "data"
HISTORY_PATH = DATA_DIR / "history.json"
DATA_DIR.mkdir(exist_ok=True)

# — LOAD VERSIONS & HISTORY —————————————————————————————
versions = sorted(p.stem for p in TESTS_DIR.glob("*.json"))
history  = {}
if HISTORY_PATH.exists():
    try:
        history = json.loads(HISTORY_PATH.read_text())
    except json.JSONDecodeError:
        history = {}

# We pick the next version after user logs in, so leave user_id blank for now
selected_version = versions[0]  # placeholder until login to history
with open(TESTS_DIR / f"{selected_version}.json") as f:
    study_words  = json.load(f)
study_sheets = chunk_dict(study_words, 4)

# — INITIALIZE STATE ———————————————————————————————————
if "phase" not in st.session_state:
    st.session_state["phase"]               = "demographics"  # start here
    st.session_state["sheet_index"]         = 0
    st.session_state["item_index"]          = 0
    st.session_state["imm_correct"]         = {}
    st.session_state["responses_immediate"] = {}
    st.session_state["free_transcript"]     = []
    st.session_state["cued_responses"]      = {}
    # also placeholders for demographics
    st.session_state["age"]      = None
    st.session_state["worry"]    = None
    st.session_state["why_worry"]= ""
    st.session_state["research_consent_name"] = ""
    st.session_state["use_audio"] = False

def setup_demographics_and_consent():
    st.title("🧠 Remindful Memory Assessment")
    st.write("""
        This 16-word test is based on a protocol 
        designed to detect early memory changes.
    """)

    # Age
    st.subheader("Your Age")
    st.session_state["age"] = st.slider("Age", 18, 100, 30, format="%d")

    # Likert worry scale
    st.subheader("How worried are you about your memory?")
    st.session_state["worry"] = st.select_slider(
        "Select one:",
        options=[
            "Not at all worried",
            "A little worried",
            "Moderately worried",
            "Very worried",
            "Extremely worried"
        ],
        value="Moderately worried"
    )
    # Optional text
    st.text_area(
        "Tell us in your own words why you chose that level (optional):",
        key="why_worry"
    )

    # Research consent name
    st.subheader("Research Consent")
    st.write("Type your full name below to consent to keeping your data for research purposes:")
    st.session_state["research_consent_name"] = st.text_input(
        "Full name", value="", key="research_name"
    )

    # Informed consent form placeholder
    st.subheader("Informed Consent Document")
    with st.expander("Click to view full consent form"):
        st.write("**[Placeholder for your full informed consent PDF or text]**")

    # Audio opt-in
    st.subheader("Audio Recording Preference")
    st.session_state["use_audio"] = st.checkbox(
        "I agree to have my spoken answers recorded (recommended for accuracy)",
        value=True
    )

    # Begin Test
    if st.button("Begin Test"):
        if not st.session_state["research_consent_name"]:
            st.error("Please type your full name to consent for research.")
            return False
        st.session_state["phase"] = "instructions"
        return True
    return False 
def instructions():
    """Display plain-language, non-plagiarised test instructions."""
    if st.session_state["phase"] != "instructions":
        return

    st.header("📋  Welcome to the Remindful Memory Check")

    st.markdown(
        """
        In this quick exercise you’ll **learn 16 everyday words** that belong to different
        categories (for example, a kind of fruit or an item of clothing).  
        We’ll guide you with gentle hints and then ask you to remember the words—first on
        your own and later with helpful category clues.

        **How it unfolds**

        1. **Learning rounds** (about 4 minutes)  
           • Four words will appear on-screen with one category cue.  
           • Choose the word that fits the cue and *say it out loud* if you can—
             speaking often strengthens memory.  
           
        2. **Quick check**  
           Right after each set, we’ll give the cue again to see if the word
           comes back to you.

        3. **Short distraction**  
           You’ll do a brief counting task so the words can “settle” in memory.

        4. **Free recall** (90 s)  
           Tell us every word you remember—in any order.  
           You may type them or record your voice.

        5. **Helpful hints**  
           For any word you missed, we’ll repeat its category to see if that jogs
           your memory.

        The whole session usually takes **under ten minutes**.

        ---
        ### Before you begin
        * • Find a quiet place and turn your volume up so you can hear the cues.  
        * • Choose **Record my voice** below if you’re comfortable speaking your answers
          (typing always works too).  
        * • There are no right-or-wrong consequences—just do your best.

        When you’re ready, press **Start**.
        """
    )

    if st.button("Start the Test"):
        st.session_state["phase"] = "controlled"
def main():
    show_progress()
    # Demographics & Consent
    if st.session_state["phase"] == "demographics":
        if not setup_demographics_and_consent():
            return

    # Instructions page
    if st.session_state["phase"] == "instructions":
        instructions()

    # Test phases
    phase = st.session_state["phase"]
    if phase == "controlled":
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

def controlled_learning():
    if st.session_state["phase"] != "controlled":
        return

    idx      = st.session_state["sheet_index"]
    item_idx = st.session_state["item_index"]
    sheet    = study_sheets[idx]
    cues     = list(sheet.keys())
    cue      = cues[item_idx]
    target   = sheet[cue]

    # Style cards
    components.html("""
      <style>
        .card { border:2px solid #888; border-radius:8px; padding:12px; margin:8px; }
        .word { font-size:36px; text-align:center; margin-bottom:8px; }
      </style>
    """, height=0)

    # at start of controlled_learning()
    cue_key = f"spoken_{idx}_{item_idx}"
    if not st.session_state.get(cue_key):
        components.html(f"""
            <script>
              const msg = new SpeechSynthesisUtterance("The Category is: {cue}");
              window.speechSynthesis.speak(msg);
            </script>
        """, height=0)
        st.session_state[cue_key] = True

    # Header & Cue
    st.header(f"Controlled Learning — Sheet {idx+1} of {len(study_sheets)}")
    st.markdown(f"<h2 style='text-align:center;'>Cue: {cue}</h2>", unsafe_allow_html=True)

    # 2×2 grid of word-cards
    words = list(sheet.values())
    cols  = st.columns(2)
    for i, word in enumerate(words):
        with cols[i % 2]:
            st.markdown(
                f"<div class='card'><div class='word'>{word}</div></div>",
                unsafe_allow_html=True
            )
            if st.button("Select", key=f"ctrl_{idx}_{item_idx}_{i}"):
                # Record if opted in
                if st.session_state.get("use_audio", False):
                    st.info("Press Record and say the matching word, then click its card.")
                    audio_learn = record_audio(key=f"learn_pre_{idx}_{item_idx}")
                    if audio_learn:
                        said = transcribe_audio(audio_learn).strip().lower()
                        st.write(f"You said: **{said}**")
                # Check click
                if word == target:
                    st.success("✅ Correct!")
                    st.session_state["item_index"] += 1
                    if st.session_state["item_index"] >= len(cues):
                        st.session_state["phase"] = "immediate"
                    return
                else:
                    st.error(f"❌ Not quite—correct word was **{target}**.")
                    return

def immediate_cued_recall():
    """Single-cue immediate recall with optional audio, one retry allowed."""
    if st.session_state["phase"] != "immediate":
        return

    idx   = st.session_state["sheet_index"]     # 0-based sheet number
    sheet = study_sheets[idx]                   # {cue: word}

    # --- create / fetch per-sheet correctness tracker ------------------
    flags = st.session_state["imm_correct"].setdefault(
        idx, {cue: False for cue in sheet}
    )

    # --- pick the first cue still unanswered --------------------------
    try:
        cue, word = next((c, w) for c, w in sheet.items() if not flags[c])
    except StopIteration:
        # All four cues done → move on
        st.session_state["sheet_index"] += 1
        st.session_state["item_index"] = 0
        st.session_state["phase"] = "controlled" if st.session_state["sheet_index"] < len(study_sheets) else "interference"
        st.experimental_rerun()
        return

    # ------------------------------------------------------------------
    st.header(f"Immediate Recall — Sheet {idx+1}/{len(study_sheets)}")
    done = sum(flags.values())
    st.progress(done/4, text=f"{done}/4 cues finished")

    # --- speak cue only once ------------------------------------------
    spoken_key = f"imm_spoken_{idx}_{cue}"
    if not st.session_state.get(spoken_key):
        speak_text(f"The category is {cue}.")
        time.sleep(1.2)  # ensure mic is free
        st.session_state[spoken_key] = True

    st.markdown(f"### What was the **{cue}**?")

    # --- gather typed or spoken answer --------------------------------
    typed = st.text_input("Type here (or leave blank if recording):",
                          key=f"imm_type_{idx}_{cue}")
    audio_resp = None
    if st.session_state.get("use_audio", False):
        audio_file = record_audio(key=f"imm_audio_{idx}_{cue}")
        if audio_file:
            audio_resp = transcribe_audio(audio_file).strip().lower()
            st.write(f"You said: **{audio_resp}**")

    # Flag to know whether we've already offered a retry
    retry_flag = st.session_state.get(f"imm_retry_{idx}_{cue}", False)

    if st.button("Next", key=f"imm_next_{idx}_{cue}"):
        response = (audio_resp or typed).strip().lower()
        if not response:
            st.warning("Please type or say a word before continuing.")
            st.stop()

        if response == word.lower():
            st.success("✅ Correct!")
            flags[cue] = True
            st.experimental_rerun()

        if not retry_flag:
            # first miss → give guided retry
            st.session_state[f"imm_retry_{idx}_{cue}"] = True
            speak_text(f"The correct answer was {word}. Let's try again. What was the {cue}?")
            st.experimental_rerun()
        else:
            # second miss → mark finished and move on
            st.error(f"❌ We'll move on. The word was **{word}**.")
            flags[cue] = True
            st.experimental_rerun()


def interference_phase():
    """Interactive distraction task: tap when the number is a multiple of 3."""
    if st.session_state["phase"] != "interference":
        return

    st.header("🧩 Distraction Round (20 s)")

    # ---------- first visit ----------
    if "int_start" not in st.session_state:
        st.markdown(
            """
            For the next 20 seconds you’ll see random numbers.  
            **Press the green Tap button whenever a number is divisible by 3.**  
            """
        )
        if st.button("Begin"):
            st.session_state["int_start"] = datetime.now()
            st.session_state["int_end"]   = st.session_state["int_start"] + timedelta(seconds=20)
            st.session_state["int_hits"]  = 0
            st.session_state["int_num"]   = None
            st.experimental_rerun()
        return

    # ---------- task in-progress ----------
    remaining = (st.session_state["int_end"] - datetime.now()).total_seconds()

    if remaining <= 0:
        st.success(f"Time’s up! You caught **{st.session_state['int_hits']}** multiples of 3 🎉")
        if st.button("Continue to Recall"):
            for k in ("int_start", "int_end", "int_hits", "int_num"):
                st.session_state.pop(k, None)
            st.session_state["phase"] = "free_recall"
            st.experimental_rerun()
        return

    # show / refresh random number
    if st.session_state["int_num"] is None or st.button("Next number"):
        st.session_state["int_num"] = random.randint(10, 99)

    st.markdown(f"<h1 style='text-align:center'>{st.session_state['int_num']}</h1>", unsafe_allow_html=True)

    # big tap button
    if st.button("✅ Tap", key="tap_btn"):
        if st.session_state["int_num"] % 3 == 0:
            st.session_state["int_hits"] += 1
        st.session_state["int_num"] = random.randint(10, 99)

    # visual timer bar
    st.progress((20 - remaining) / 20)

def free_recall_phase():
    if st.session_state["phase"] != "free_recall":
        return

    st.header("Free Recall (90 s)")
    st.write("Say (or type) all the words you remember.")

    if st.session_state.get("use_audio", False):
        audio_file = record_audio(key="free_recall")
        if audio_file:
            txt = transcribe_audio(audio_file)
            st.session_state["free_transcript"] = txt.split()
            st.write("You said:", st.session_state["free_transcript"])
    else:
        txt = st.text_area("Type remembered words, separated by commas:", height=220)
        if txt:
            st.session_state["free_transcript"] = [w.strip() for w in txt.split(",") if w.strip()]

    if st.button("Done Free Recall"):
        st.session_state["phase"] = "cued_recall"

def cued_recall_phase():
    """Final cued recall — typed or spoken answer with Next button."""
    if st.session_state["phase"] != "cued_recall":
        return

    # figure out which cue we’re on
    if "cue_iter" not in st.session_state:
        st.session_state["cue_iter"] = iter([
            (cue, word) for cue, word in study_words.items()
            if word.lower() not in
               {w.lower() for w in st.session_state["free_transcript"]}
        ])

    try:
        cue, word = st.session_state.get("current_cue", next(st.session_state["cue_iter"]))
        st.session_state["current_cue"] = (cue, word)
    except StopIteration:
        # all cues handled → results
        st.session_state.pop("cue_iter", None)
        st.session_state.pop("current_cue", None)
        st.session_state["phase"] = "results"
        st.experimental_rerun()
        return

    st.header("Cued Recall")
    st.markdown(f"### What was the **{cue}**?")

    typed = st.text_input("Type here (optional):", key=f"cr_type_{cue}")
    audio_resp = None
    if st.session_state.get("use_audio", False):
        audio_file = record_audio(key=f"cr_audio_{cue}")
        if audio_file:
            audio_resp = transcribe_audio(audio_file).strip().lower()
            st.write(f"You said: **{audio_resp}**")

    if st.button("Next", key=f"cr_next_{cue}"):
        response = (audio_resp or typed).strip().lower()
        # store even blank to mark progression
        st.session_state["cued_responses"][cue] = response
        # proceed to next cue
        st.session_state.pop("current_cue", None)
        st.experimental_rerun()

    if st.button("See Results"):
        st.session_state["phase"] = "results"

def show_results():
    if st.session_state["phase"] != "results":
        return

    # Immediate Recall
    imm_score, _ = score_responses(
        study_words, st.session_state["responses_immediate"]
    )
    # Free Recall
    free_norm = {w.lower() for w in st.session_state["free_transcript"]}
    free_score= sum(1 for w in study_words.values() if w.lower() in free_norm)
    # Cued Recall & Intrusions
    missed     = {
        cue:word for cue,word in study_words.items()
        if word.lower() not in free_norm
    }
    cr_resp    = st.session_state["cued_responses"]
    cr_score   = sum(
        1 for cue,word in missed.items()
        if cr_resp.get(cue,"").lower().strip() == word.lower()
    )
    intrusions = sum(
        1 for cue,resp in cr_resp.items()
        if cue in missed and resp.lower().strip() != missed[cue].lower()
    )

    total = imm_score + free_score + cr_score

    st.header("Your Memory Snapshot")

    cols = st.columns(2)
    with cols[0]:
        st.metric("Immediate recall", f"{imm_score} / 16")
        st.metric("Free recall",      f"{free_score} / 16")
    with cols[1]:
        st.metric("Cued recall",      f"{cr_score} / {len(missed)}")
        st.metric("Intrusions",       intrusions)
    
    st.subheader("What do these numbers mean?")
    st.write(
        """
        • Most healthy adults score **10–14** on free recall and improve with cues.  
        • Intrusions (words that weren't on the list) are common; one or two is normal.  
        • If you are concerned about your memory, share these results with a healthcare
          professional—they can place them in the context of a full assessment.
        """
    )
    
    st.download_button("📥 Download my results", data=str({
            "immediate": imm_score,
            "free": free_score,
            "cued": cr_score,
            "intrusions": intrusions,
            "total": total
        }),
        file_name="Remindful_results.txt")
    
if __name__ == "__main__":
    main()
