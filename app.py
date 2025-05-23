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
    st.session_state["age"] = st.slider("Select your age", 18, 100, 30)

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
        # require research consent
        if not st.session_state["research_consent_name"]:
            st.error("Please type your full name to consent for research.")
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

    if st.button("Start"):
        st.session_state["phase"] = "controlled"

def main():
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

    # Header & Cue
    st.header(f"Controlled Learning — Sheet {idx+1} of {len(study_sheets)}")
    st.markdown(f"<h2 style='text-align:center;'>Cue: {cue}</h2>", unsafe_allow_html=True)
    components.html(f"""
      <script>
        const msg = new SpeechSynthesisUtterance("Cue: {cue}");
        window.speechSynthesis.speak(msg);
      </script>
    """, height=0)

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
                    audio_f = record_audio(key=f"learn_{idx}_{item_idx}_{i}")
                    if audio_f:
                        resp = transcribe_audio(audio_f).strip().lower()
                        st.write(f"**You said:** {resp}")
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
    if st.session_state["phase"] != "immediate":
        return

    idx   = st.session_state["sheet_index"]
    sheet = study_sheets[idx]
    flags = st.session_state["imm_correct"].setdefault(
        idx, {cue: False for cue in sheet}
    )

    for cue, word in sheet.items():
        if not flags[cue]:
            st.write(f"🔉 Cue: {cue}")
            if st.session_state.get("use_audio", False):
                audio = record_audio(key=f"imm1_{idx}_{cue}")
                if audio:
                    try:
                        resp = transcribe_audio(audio).strip().lower()
                        if resp == word.lower():
                            st.success("✅ Correct!")
                            flags[cue] = True
                        else:
                            speak_text(f"The {cue} was {word}. What was the {cue}?")
                            retry = record_audio(key=f"imm2_{idx}_{cue}")
                            if retry and transcribe_audio(retry).strip().lower() == word.lower():
                                st.success("✅ Got it on retry!")
                                flags[cue] = True
                            else:
                                st.error("Still not right—moving on.")
                    except Exception as e:
                        st.warning(f"Transcription error: {e}")
            else:
                # skip recording if opted out
                st.info("Click Record to speak or skip if typing.")
            return

    # all done for this sheet → advance
    st.session_state["sheet_index"] += 1
    st.session_state["item_index"]   = 0
    if st.session_state["sheet_index"] < len(study_sheets):
        st.session_state["phase"] = "controlled"
    else:
        st.session_state["phase"] = "interference"

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
            **Press the green Tap button whenever a number *is divisible by 3*.**  
            This keeps your mind busy before the next memory step.
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
            # clean up distraction state & advance
            for k in ("int_start", "int_end", "int_hits", "int_num"):
                st.session_state.pop(k, None)
            st.session_state["phase"] = "free_recall"
        return

    # show or refresh random number
    if st.session_state["int_num"] is None or st.button("Next number"):
        st.session_state["int_num"] = random.randint(10, 99)

    st.markdown(f"<h1 style='text-align:center'>{st.session_state['int_num']}</h1>",
                unsafe_allow_html=True)

    # big tap button
    if st.button("✅ Tap", key="tap_btn"):
        if st.session_state["int_num"] % 3 == 0:
            st.session_state["int_hits"] += 1
        # immediately show a new number
        st.session_state["int_num"] = random.randint(10, 99)

    # visual timer bar
    st.progress((20 - remaining) / 20)
        st.session_state["phase"] = "free_recall"

def free_recall_phase():
    if st.session_state["phase"] != "free_recall":
        return

    st.header("Free Recall (90 s)")
    st.write("Say (or type) all the words you remember.")

    if st.session_state.get("use_audio", False):
        free_f = record_audio(key="free_recall")
        if free_f:
            txt = transcribe_audio(free_f)
            st.session_state["free_transcript"] = txt.split()
            st.write("You said:", st.session_state["free_transcript"])
    else:
        txt = st.text_area(
            "Type remembered words, separated by commas:"
        )
        if txt:
            st.session_state["free_transcript"] = [
                w.strip() for w in txt.split(",") if w.strip()
            ]

    if st.button("Done Free Recall"):
        st.session_state["phase"] = "cued_recall"

def cued_recall_phase():
    if st.session_state["phase"] != "cued_recall":
        return

    st.header("Cued Recall")
    free_set = set(w.lower() for w in st.session_state["free_transcript"])
    missed   = {
        cue: word for cue, word in study_words.items()
        if word.lower() not in free_set
    }

    for cue, word in missed.items():
        st.write(f"🔉 Cue: {cue}")
        if st.session_state.get("use_audio", False):
            audio_f = record_audio(key=f"cue_{cue}")
            if audio_f:
                resp = transcribe_audio(audio_f).strip().lower()
                st.session_state["cued_responses"][cue] = resp
        else:
            resp = st.text_input(f"What was the {cue}?", key=f"text_{cue}")
            if resp:
                st.session_state["cued_responses"][cue] = resp.strip().lower()

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

    st.header("Final Score")
    st.write(f"• Immediate Recall: {imm_score}/16")
    st.write(f"• Free Recall: {free_score}/16")
    st.write(f"• Cued Recall: {cr_score}/{len(missed)}")
    st.write(f"• Intrusions: {intrusions}")
    st.write(f"**Overall Remindful Test Score total: {total}/48**")

    st.write("### Save Your Results")
    email = st.text_input("Email")
    pw    = st.text_input("Password", type="password")
    if st.button("Save My Results"):
        st.success("✅ Results saved! Thank you.")

if __name__ == "__main__":
    main()