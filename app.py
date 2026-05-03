"""
app.py - VoterMitra: India Election Assistant
Features: Hindi/English toggle, Voice input (Hindi + English), Audio output (gTTS)
"""

import streamlit as st
import urllib.parse
import json
import os
import io
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from google.genai import types
from utils.llm import get_gemini_model, create_chat_session, ask_votermitra, check_eligibility, translate_messages, extract_age_from_id, summarize_candidate
from utils.translations import LANGUAGES, UI_TRANSLATIONS

load_dotenv()

# Validate GEMINI_API_KEY environment variable
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("GEMINI_API_KEY environment variable is not set. Please configure it to use VoterMitra.")
    st.stop()

st.set_page_config(
    page_title="VoterMitra - India Election Assistant",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize language state (single initialization)
if "lang" not in st.session_state:
    st.session_state["lang"] = "en"

@st.cache_data
def load_kb(lang):
    kb_file = f"election_knowledge_{lang}.json" if lang != "en" else "election_knowledge.json"
    kb_path = Path(__file__).parent / "data" / kb_file
    
    if not kb_path.exists():
        kb_path = Path(__file__).parent / "data" / "election_knowledge.json"
        
    with open(kb_path, "r", encoding="utf-8") as f:
        return json.load(f)

kb = load_kb(st.session_state["lang"])

@st.cache_data
def load_candidates():
    c_path = Path(__file__).parent / "data" / "candidates.json"
    if c_path.exists():
        with open(c_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

candidates_data = load_candidates()

@st.cache_data
def load_styles():
    """Load CSS from assets/styles.css"""
    styles_path = Path(__file__).parent / "assets" / "styles.css"
    if styles_path.exists():
        with open(styles_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def t(key, **kwargs):
    """Translate key with placeholder support and graceful missing key handling."""
    lang = st.session_state["lang"]
    if key in UI_TRANSLATIONS:
        text = UI_TRANSLATIONS[key].get(lang, UI_TRANSLATIONS[key].get("en", ""))
        if text:
            try:
                return text.format(**kwargs) if kwargs else text
            except KeyError as e:
                # Log missing placeholder but return partial text
                print(f"Missing placeholder in {key}: {e}")
                return text
    return ""

def text_to_speech(text: str, lang: str = "en") -> bytes:
    try:
        from gtts import gTTS
        tts_lang = "hi" if lang == "hi" else "en"
        clean_text = text.replace("*", "").replace("#", "").replace("_", "").replace("Tip: ", "").replace("⭐", "")
        tts = gTTS(text=clean_text, lang=tts_lang, slow=False)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return audio_buffer.read()
    except Exception as e:
        st.warning(f"Audio generation failed: {e}")
        return None

def detect_language(text: str) -> str:
    for char in text:
        if '\u0900' <= char <= '\u097F':
            return "hi"
    return "en"

def transcribe_audio(audio_bytes: bytes, lang: str = "en") -> str:
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        with sr.AudioFile(tmp_path) as source:
            audio = recognizer.record(source)
        sr_lang = "hi-IN" if lang == "hi" else "en-IN"
        text = recognizer.recognize_google(audio, language=sr_lang)
        os.unlink(tmp_path)
        return text
    except Exception as e:
        return f"Could not transcribe: {e}"

# Load and apply CSS
css_styles = load_styles()
if css_styles:
    st.markdown(f"<style>{css_styles}</style>", unsafe_allow_html=True)

st.title(t('title'))
st.markdown(f"#### {t('subtitle')}")

with st.sidebar:
    st.markdown(f"### 🌐 {t('language_label')}")
    lang_options = list(LANGUAGES.keys())
    current_lang_idx = lang_options.index(st.session_state["lang"])
    
    selected_lang = st.selectbox(
        "Select Language",
        lang_options,
        index=current_lang_idx,
        format_func=lambda x: LANGUAGES[x],
        key="lang_select",
        label_visibility="collapsed"
    )
    
    if selected_lang != st.session_state["lang"]:
        st.session_state["lang"] = selected_lang
        # Trigger translation if needed
        if "messages" in st.session_state and st.session_state["messages"]:
            model = st.session_state.get("model")
            if model:
                target_lang_name = LANGUAGES[selected_lang]
                translate_messages(model, st.session_state["messages"], target_lang_name)
        st.rerun()

    st.divider()
    st.markdown(f"### 📚 {t('quick_topics_label')}")
    questions = t("quick_questions")
    for q in questions:
        if st.button(q, key=f"quick_{q}", use_container_width=True):
            st.session_state["prefill_question"] = q

    st.divider()
    st.markdown(f"### 📞 {t('helplines_label')}")
    st.info(f"**{t('voter_helpline_text')}**\n\n**{t('eci_portal_text')}**\n\n**{t('cvigil_text')}**")

    st.divider()
    if st.button(t("clear_chat"), key="sidebar_clear_chat", use_container_width=True):
        st.session_state["messages"] = []
        st.session_state["chat_session"] = None
        st.rerun()

tab_chat, tab_timeline, tab_eligibility, tab_candidates, tab_simulator, tab_guide = st.tabs([
    t("tab_chat"), t("tab_timeline"), t("tab_eligibility"), t("tab_candidates"), t("tab_simulator"), t("tab_guide")
])

# TAB 1: CHAT
with tab_chat:
    if "model" not in st.session_state:
        try:
            st.session_state["model"] = get_gemini_model()
        except Exception as e:
            st.error(f"Could not connect to Gemini: {e}")
            st.stop()

    if "chat_session" not in st.session_state or st.session_state["chat_session"] is None:
        history = []
        if "messages" in st.session_state:
            for m in st.session_state["messages"]:
                role = "model" if m["role"] == "assistant" else "user"
                history.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))
        st.session_state["chat_session"] = create_chat_session(st.session_state["model"], kb, history=history)

    if "messages" not in st.session_state or not st.session_state["messages"]:
        st.session_state["messages"] = [{"role": "assistant", "content": t("welcome")}]

    # Compact inline mic - sits beside the Streamlit chat input bar
    SPEECH_CODES = {"en": "en-IN", "hi": "hi-IN", "bn": "bn-IN", "mr": "mr-IN", "ta": "ta-IN"}
    speech_lang_code = SPEECH_CODES.get(st.session_state["lang"], "en-IN")

    # Load mic handler script
    mic_script_path = Path(__file__).parent / "assets" / "mic_handler.js"
    mic_html = ""
    if mic_script_path.exists():
        with open(mic_script_path, "r", encoding="utf-8") as f:
            mic_js_content = f.read()
        mic_html = f"""
        <script>
        const speechLangCode = '{speech_lang_code}';
        {mic_js_content}
        </script>
        """

    audio_output = st.toggle(f"🔊 {t('read_aloud')}", value=False, key="audio_toggle")

    for msg in st.session_state["messages"]:
        avatar = "🗳️" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and audio_output and msg.get("audio"):
                st.audio(msg["audio"], format="audio/mp3")
                st.markdown(f'<div class="voice-wave"><div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div><span style="font-size:0.7rem; color:#8e44ad; font-style:italic;">{t("ai_speaking")}</span></div>', unsafe_allow_html=True)

    prefill = st.session_state.pop("prefill_question", None)
    user_input = st.chat_input(t("chat_placeholder")) or prefill

    # Render mic button script (invisible iframe)
    st.components.v1.html(mic_html, height=0)

    if user_input:
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
        st.session_state["messages"].append({"role": "user", "content": user_input})

        # UI language (toggle) takes full priority.
        lang_name = LANGUAGES.get(st.session_state["lang"], "English").split("(")[-1].strip(")")
        # Fact-Check Grounding Instruction
        grounding = " You are an official Election Assistant grounded in the Election Commission of India (ECI) Handbook. Only provide legally and procedurally accurate information."
        query = f"Please respond ONLY in {lang_name} (Preserve all markdown formatting). {grounding} User Question: {user_input}"

        with st.chat_message("assistant", avatar="🗳️"):
            with st.spinner(f"{t('thinking')} {lang_name}..."):
                response = ask_votermitra(st.session_state["chat_session"], query)
            st.markdown(response)

            audio_data = None
            if audio_output:
                resp_lang = detect_language(response)
                with st.spinner("🎙️ Generating audio..."):
                    audio_data = text_to_speech(response, lang=resp_lang)
                if audio_data:
                    st.audio(audio_data, format="audio/mp3")

        st.session_state["messages"].append({"role": "assistant", "content": response, "audio": audio_data})
        st.rerun()

# TAB 2: TIMELINE
with tab_timeline:
    st.markdown(f"## {t('tab_timeline')}", help="Election timeline and process phases - ARIA Label: Election Process Timeline")

    phases = kb["election_process_phases"]
    phase_icons = ["📢", "📝", "🔍", "🗳️", "🚚", "📊", "🏆", "📜"]
    for i, phase in enumerate(phases):
        with st.expander(f"{phase_icons[i]} {phase.get('phase_label', 'Phase')} {phase['phase']}: {phase['name']}", expanded=(i == 0)):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{phase['description']}**")
                st.markdown(f"**{t('key_events_label') if 'key_events_label' in UI_TRANSLATIONS else 'Key Events:'}**")
                for event in phase["key_events"]:
                    st.markdown(f"- {event}")
            with col2:
                # Google Calendar "Remind Me" Integration
                cal_text = urllib.parse.quote(f"Election Event: {phase['name']}")
                cal_details = urllib.parse.quote(f"Election Phase: {phase['name']} - {phase['description']}")
                # Simulated dates for link payload 
                cal_url = f"https://calendar.google.com/calendar/u/0/r/eventedit?text={cal_text}&details={cal_details}"
                
                st.markdown(f"""
                <div style='text-align:right; display: flex; flex-direction: column; align-items: flex-end; gap: 8px;'>
                    <div>
                        <small>{t('typical_duration_label')}</small><br>
                        <b>{phase['typical_duration']}</b>
                    </div>
                    <a href='{cal_url}' target='_blank' style='text-decoration:none;'>
                        <button aria-label='Remind Me via Google Calendar' style='cursor: pointer; padding: 6px 12px; border-radius: 4px; border: none; font-size: 0.8rem; background-color: #ff4b4b; color: white; transition: background-color 0.3s;'>{t('remind_me')}</button>
                    </a>
                </div>
                """, unsafe_allow_html=True)

    st.divider()
    st.markdown("### 🏛️ Types of Elections in India")
    etype_icons = ["🏛️", "🏘️", "📜", "🏙️", "🔄"]
    cols = st.columns(len(kb["election_types"]))
    for i, etype in enumerate(kb["election_types"]):
        with cols[i % len(cols)]:
            st.markdown(f"#### {etype_icons[i % len(etype_icons)]}\n**{etype['name']}**")
            st.caption(etype['description'])
            if "frequency" in etype:
                st.markdown(f"🔄 _{etype['frequency']}_")

# TAB 3: ELIGIBILITY
with tab_eligibility:
    st.markdown(f"## {t('tab_eligibility')}")

    st.info(f"📸 **{t('smart_fill_info')}**")
    
    uploaded_file = st.file_uploader(t('upload_id'), type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        if "last_uploaded" not in st.session_state or st.session_state["last_uploaded"] != uploaded_file.name:
            with st.spinner(t('scanning_id')):
                image_data = uploaded_file.getvalue()
                model = st.session_state.get("model")
                if model:
                    extracted = extract_age_from_id(model, image_data)
                    st.session_state["extracted_age"] = extracted
                    st.session_state["last_uploaded"] = uploaded_file.name

    default_age = st.session_state.get("extracted_age", 20)

    with st.form("eligibility_form"):
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input(t('your_age'), min_value=1, max_value=120, value=default_age)
            is_citizen = st.radio(t('indian_citizen'), [f"{t('yes_label')} / हाँ", f"{t('no_label')} / नहीं"]) == f"{t('yes_label')} / हाँ"
        with col2:
            is_resident = st.radio(t('resident_india'), [f"{t('yes_label')} / हाँ", f"{t('no_nri_label')} / नहीं (NRI)"]) == f"{t('yes_label')} / हाँ"
            disqualified = st.checkbox(t('disqualification_label'), value=False)
        submitted = st.form_submit_button(t('check_eligibility_btn'), use_container_width=True)

    if submitted:
        result = check_eligibility(age, is_citizen, is_resident, disqualified, lang=st.session_state["lang"])
        if result["eligible"]:
            st.success(f"✅ **{t('eligible_success')}**")
        else:
            st.error(f"❌ **{t('eligible_error')}**")
        for reason in result["reasons"]:
            st.markdown(f"- {reason}")
        if result["next_steps"]:
            st.markdown(f"**{t('next_steps_label')}**")
            for i, step in enumerate(result["next_steps"], 1):
                st.markdown(f"{i}. {step}")

    st.divider()
    st.markdown(f"### 🆔 {t('alternate_ids_label')}")
    st.markdown(t('no_id_voting_info'))
    cols = st.columns(3)
    for i, id_doc in enumerate(kb["alternate_ids_for_voting"]):
        with cols[i % 3]:
            st.markdown(f"<span class='info-chip'>{id_doc}</span>", unsafe_allow_html=True)

# TAB 4: CANDIDATES
with tab_candidates:
    st.markdown(f"## {t('tab_candidates')}")
    st.info(f"📍 {t('pincode_info')}")
    
    pincode = st.text_input(t('pincode_label'), placeholder="110001")
    
    if pincode:
        found_constituency = None
        for item in candidates_data:
            if pincode in item["pincodes"]:
                found_constituency = item
                break
        
        if found_constituency:
            st.success(f"{t('constituency_found')}: **{found_constituency['constituency']}, {found_constituency['state']}**")
            
            # Google Maps Embed (Simulated map view using OpenStreetMap for generic display or specific query)
            map_query = urllib.parse.quote(f"{found_constituency['constituency']}, {found_constituency['state']}, India")
            st.components.v1.iframe(f"https://maps.google.com/maps?q={map_query}&t=&z=13&ie=UTF8&iwloc=&output=embed", height=300)
            
            for cand in found_constituency["candidates"]:
                with st.expander(f"📋 {t('affidavit_summary')}: {cand['name']}", expanded=True):
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.markdown(f"**{t('party')}:** {cand['party']}")
                        st.markdown(f"**{t('education')}:** {cand['education']}")
                        st.markdown(f"**{t('profession')}:** {cand['profession']}")
                    with col2:
                        st.markdown(f"**{t('assets')}:** Rs. {cand['total_assets_inr']}")
                        st.markdown(f"**{t('liabilities')}:** Rs. {cand['total_liabilities_inr']}")
                        st.markdown(f"**{t('criminal_cases')}:** {cand['criminal_cases']}")
                    
                    st.caption(f"ℹ️ {t('ai_note')}")
                    if st.button(t('view_summary'), key=f"sum_{cand['name']}"):
                        model = st.session_state.get("model")
                        if model:
                            with st.spinner(t('analyzing_affidavit')):
                                lang_name = LANGUAGES.get(st.session_state["lang"], "English").split("(")[-1].strip(")")
                                summary = summarize_candidate(model, cand, lang_name)
                                st.markdown("---")
                                st.markdown(f"### 🤖 {t('ai_summary')} ({lang_name})")
                                st.markdown(summary)
                        else:
                            st.error(t('ai_not_init'))
        else:
            st.warning(t('no_data_found'))

# TAB 5: SIMULATOR
with tab_simulator:
    st.markdown(f"## {t('tab_simulator')}", help="Interactive voting simulator - ARIA Label: Voting Process Simulator")

    if "sim_step" not in st.session_state:
        st.session_state["sim_step"] = 1
    
    progress_val = (st.session_state["sim_step"] - 1) / 3
    st.progress(progress_val)
    
    col_vis, col_text = st.columns([1, 1])
    
    if st.session_state["sim_step"] == 1:
        with col_vis:
            st.markdown('<div class="sim-container" aria-label="Step 1 Vis"><div class="map-base"><div class="map-grid"></div><div class="map-pin">📍</div></div></div>', unsafe_allow_html=True)
        with col_text:
            st.markdown(f"### {t('sim_step1_title')}")
            st.markdown(t("sim_step1_desc"))
            if st.button(t("sim_step1_btn"), use_container_width=True, type="primary"):
                st.session_state["sim_step"] = 2
                st.rerun()

    elif st.session_state["sim_step"] == 2:
        with col_vis:
            st.markdown('<div class="sim-container" aria-label="Step 2 Vis"><div class="finger-box"><div class="ink-droplet"></div><div class="css-finger"><div class="css-nail"></div><div class="finger-ink-tip"></div></div></div></div>', unsafe_allow_html=True)
        with col_text:
            st.markdown(f"### {t('sim_step2_title')}")
            st.markdown(t("sim_step2_desc"))
            if st.button(t("sim_step2_btn"), use_container_width=True, type="primary"):
                st.session_state["sim_step"] = 3
                st.rerun()

    elif st.session_state["sim_step"] == 3:
        with col_vis:
            evm_html = f"""
            <style>
            .evm-container {{ perspective: 1000px; display: flex; justify-content: center; }}
            .evm-panel {{ width: 240px; background: #ecf0f1; border-radius: 12px; transform: rotateX(15deg); box-shadow: 0 15px 30px rgba(0,0,0,0.1); padding: 15px; border: 2px solid #bdc3c7; }}
            .evm-row {{ display: flex; align-items: center; justify-content: space-between; padding: 6px; border-bottom: 1px solid #ddd; }}
            .evm-btn {{ width: 40px; height: 30px; background: #3498db; border: none; border-radius: 4px; box-shadow: 0 4px #2980b9; cursor: pointer; }}
            .evm-light {{ width: 10px; height: 10px; background: #2ecc71; border-radius: 50%; box-shadow: 0 0 8px #2ecc71; }}
            </style>
            <div class="evm-container" role="region" aria-label="EVM Machine Display">
                <div class="evm-panel">
                    <div style="background:#34495e; height:40px; border-radius:6px; margin-bottom:12px; display:flex; align-items:center; padding:0 12px;">
                        <div class="evm-light"></div><span style="color:white; font-size:11px; margin-left:10px; font-family:sans-serif;">{t('evm_ready')}</span>
                    </div>
                    <div class="evm-row"><span style="font-size:10px; font-weight:bold;">{t('candidate')} A</span><button class="evm-btn" aria-label="Vote for Candidate A"></button></div>
                    <div class="evm-row"><span style="font-size:10px; font-weight:bold;">{t('candidate')} B</span><button class="evm-btn" aria-label="Vote for Candidate B"></button></div>
                    <div class="evm-row"><span style="font-size:10px; font-weight:bold;">NOTA</span><button class="evm-btn" aria-label="Vote None of the Above"></button></div>
                </div>
            </div>
            """
            st.components.v1.html(evm_html, height=320)
        with col_text:
            st.markdown(f"### {t('sim_step3_title')}")
            st.markdown(t("sim_step3_desc"))

            if st.button(t("vote_btn"), use_container_width=True, type="primary", key="vote_button"):
                st.components.v1.html('<audio autoplay><source src="https://www.soundjay.com/buttons/beep-01a.mp3" type="audio/mpeg"></audio>', height=0)
                st.toast(t("vote_recorded"), icon="🗳️")
                import time
                time.sleep(1.5)
                st.session_state["sim_step"] = 4
                st.rerun()

    elif st.session_state["sim_step"] == 4:
        with col_vis:
            st.markdown('<div class="sim-container" aria-label="Step 4 Vis"><div class="vvpat-box"><div class="vvpat-window"><div class="vvpat-slip"></div></div></div></div>', unsafe_allow_html=True)
        with col_text:
            st.markdown(f"### {t('sim_step4_title')}")
            st.markdown(t("sim_step4_desc"))
            st.success(f"✅ **{t('vote_verified')}**")

            if st.button(t("sim_reset"), use_container_width=True):
                st.session_state["sim_step"] = 1
                st.rerun()

# TAB 6: VOTER GUIDE
with tab_guide:
    st.markdown(f"## {t('tab_guide')}")
    st.markdown(f"### 🗳️ {t('reg_as_voter')}")
    reg = kb["voter_registration"]
    for i, step in enumerate(reg["steps"], 1):
        st.markdown(f"**{i}.** {step}")

    st.divider()
    st.markdown(f"### 📂 {t('docs_req')}")
    for doc in reg["documents_required"]:
        st.markdown(f"- {doc}")

    st.markdown(f"### ❓ {t('faqs_label')}")
    for faq in kb["faq"]:
        with st.expander(f"Q: 🤔 {faq['q']}"):
            st.markdown(faq["a"])

    st.divider()
    st.markdown(f"### 👥 {t('key_officials_label')}")
    cols = st.columns(2)
    for i, official in enumerate(kb["key_officials"]):
        with cols[i % 2]:
            st.markdown(f"**{official['role']}**")
            st.caption(official["responsibility"])

    st.divider()
    st.markdown(f"### 📜 {t('mcc_rules_label')}")
    mcc = kb["model_code_of_conduct"]
    st.markdown(f"_{mcc['description']}_")
    for rule in mcc["key_rules"]:
        st.markdown(f"- {rule}")
    st.caption(f"Enforcement: {mcc['enforcement']}")

st.divider()
st.markdown("""
<div style='text-align: center; color: #888; font-size: 0.8rem;'>
    🇮🇳 VoterMitra - Built for Hack2Skill PW Virtual Hackathon &nbsp;|&nbsp;
    Data source: Election Commission of India (ECI) &nbsp;|&nbsp;
    Powered by Google Gemini AI &nbsp;|&nbsp; Politically neutral. Always.
</div>
""", unsafe_allow_html=True)
