"""
app.py - VoteBot: India Election Assistant
Features: Hindi/English toggle, Voice input (Hindi + English), Audio output (gTTS)
"""

import streamlit as st
import json
import os
import io
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from google.genai import types
from utils.llm import get_gemini_model, create_chat_session, ask_votebot, check_eligibility, translate_messages, extract_age_from_id, summarize_candidate
from utils.translations import LANGUAGES, UI_TRANSLATIONS

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

st.set_page_config(
    page_title="VoteBot - India Election Assistant",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
        with open(c_path, "r") as f:
            return json.load(f)
    return []

candidates_data = load_candidates()

if "lang" not in st.session_state:
    st.session_state["lang"] = "en"

def t(key):
    lang = st.session_state["lang"]
    if key in UI_TRANSLATIONS:
        return UI_TRANSLATIONS[key].get(lang, UI_TRANSLATIONS[key]["en"])
    return ""

def text_to_speech(text: str, lang: str = "en") -> bytes:
    try:
        from gtts import gTTS
        tts_lang = "hi" if lang == "hi" else "en"
        clean_text = text.replace("*", "").replace("#", "").replace("_", "").replace("Tip: ", "").replace("", "")
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

# --- 100% ORIGINAL CLEAN DESIGN ---
st.markdown("""
<style>
    /* The thin tricolor strip at the very top */
    [data-testid="stHeader"]::before {
        content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 6px;
        background: linear-gradient(90deg, #FF9933 33%, #fff 33%, #fff 66%, #138808 66%);
        z-index: 999;
    }
</style>
""", unsafe_allow_html=True)

st.title(f" {t('title')}")
st.markdown(f"#### {t('subtitle')}")

with st.sidebar:
    st.markdown(f"###  {t('language_label')}")
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
    st.markdown(f"###  {t('helplines_label')}")
    st.info(f"**{t('voter_helpline_text')}**\n\n**{t('eci_portal_text')}**\n\n**{t('cvigil_text')}**")

    st.divider()
    if st.button(f" {t('clear_chat')}", key="sidebar_clear_chat", use_container_width=True):
        st.session_state["messages"] = []
        st.session_state["chat_session"] = None
        st.rerun()

tab_chat, tab_timeline, tab_eligibility, tab_candidates, tab_simulator, tab_guide = st.tabs([
    t("tab_chat"), t("tab_timeline"), t("tab_eligibility"), t("tab_candidates"), t("tab_simulator"), t("tab_guide")
])

#  TAB 1: CHAT 
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
        st.session_state["chat_session"] = create_chat_session(st.session_state["model"], history=history)

    if "messages" not in st.session_state or not st.session_state["messages"]:
        st.session_state["messages"] = [{"role": "assistant", "content": t("welcome")}]

    #  Compact inline mic - sits beside the Streamlit chat input bar 
    SPEECH_CODES = {"en": "en-IN", "hi": "hi-IN", "bn": "bn-IN", "mr": "mr-IN", "ta": "ta-IN"}
    speech_lang_code = SPEECH_CODES.get(st.session_state["lang"], "en-IN")

    mic_html = f"""
    <script>
    (function() {{
      const parentDoc = window.parent.document;
      
      function inject() {{
          // Prevent multiple injections
          if (parentDoc.getElementById('micBtnWrap')) return true;

          // Find the chat input container
          const chatInputContainer = parentDoc.querySelector('[data-testid="stChatInput"]');
          if (!chatInputContainer) return false;

          // Add custom styles to parent document
          if (!parentDoc.getElementById('micStyles')) {{
            const style = parentDoc.createElement('style');
            style.id = 'micStyles';
            style.textContent = `
              #micBtnWrap {{
                position: absolute;
                right: 3.5rem;
                bottom: 50%;
                transform: translateY(50%);
                display: flex;
                align-items: center;
                z-index: 999;
              }}
              #micBtn {{
                background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Crect x='9' y='2' width='6' height='12' rx='3' fill='%23888'/%3E%3Cpath d='M5 10c0 3.866 3.134 7 7 7s7-3.134 7-7' stroke='%23888' stroke-width='2' stroke-linecap='round'/%3E%3Cline x1='12' y1='17' x2='12' y2='21' stroke='%23888' stroke-width='2' stroke-linecap='round'/%3E%3Cline x1='8' y1='21' x2='16' y2='21' stroke='%23888' stroke-width='2' stroke-linecap='round'/%3E%3C/svg%3E") no-repeat center;
                background-size: 24px;
                border: none;
                width: 32px;
                height: 32px;
                cursor: pointer;
                padding: 4px;
                border-radius: 50%;
                transition: background 0.15s, transform 0.1s;
                opacity: 0.7;
              }}
              #micBtn:hover {{ background-color: rgba(142,68,173,0.12); opacity: 1; }}
              #micBtn:active {{ transform: scale(0.9); }}
              #micBtn.listening {{ 
                animation: micpulse 0.9s infinite; 
                background-color: rgba(231, 76, 60, 0.1);
                opacity: 1;
              }}
              @keyframes micpulse {{
                0%,100% {{ box-shadow: 0 0 0px #e74c3c; }}
                50%      {{ box-shadow: 0 0 8px #e74c3c; }}
              }}
              #micStatus {{
                font-size: 0.72rem;
                color: #8e44ad;
                margin-right: 4px;
                font-style: italic;
                white-space: nowrap;
              }}
              #micStatus.active {{ color: #e74c3c; font-weight: 600; }}
            `;
            parentDoc.head.appendChild(style);
          }}

          // Ensure the chat input container has relative positioning so our absolute button aligns correctly
          chatInputContainer.style.position = 'relative';

          // Create the wrapper
          const wrap = parentDoc.createElement('div');
          wrap.id = 'micBtnWrap';

          const status = parentDoc.createElement('span');
          status.id = 'micStatus';

          const btn = parentDoc.createElement('button');
          btn.id = 'micBtn';
          btn.title = 'Click to speak / बोलने के लिए क्लिक करें';
          btn.textContent = '';

          wrap.appendChild(status);
          wrap.appendChild(btn);
          chatInputContainer.appendChild(wrap);

          const SR = window.SpeechRecognition || window.webkitSpeechRecognition;

          if (!SR) {{
            btn.title = 'Speech not supported - use Chrome/Edge';
            btn.style.opacity = '0.35';
            btn.style.cursor  = 'not-allowed';
            return true;
          }}

          const rec = new SR();
          rec.lang = '{speech_lang_code}';
          rec.interimResults = true;
          rec.maxAlternatives = 1;
          let listening = false;

          btn.addEventListener('click', () => {{ listening ? rec.stop() : rec.start(); }});

          rec.onstart = () => {{
            listening = true;
            btn.textContent = '';
            btn.classList.add('listening');
            status.textContent = '[LIVE]';
            status.classList.add('active');
          }};

          rec.onresult = (e) => {{
            let interim = '', final = '';
            for (let i = e.resultIndex; i < e.results.length; i++) {{
              const tr = e.results[i][0].transcript;
              if (e.results[i].isFinal) final += tr; else interim += tr;
            }}
            status.textContent = final || interim ? ' ' + (final || interim).slice(0,24) + '...' : '[LIVE]';
            if (final) {{
              const ta = parentDoc.querySelector('textarea[data-testid="stChatInputTextArea"]');
              if (ta) {{
                Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value')
                  .set.call(ta, final);
                ta.dispatchEvent(new Event('input', {{bubbles:true}}));
                setTimeout(() => ta.dispatchEvent(
                  new KeyboardEvent('keydown', {{key:'Enter',code:'Enter',keyCode:13,bubbles:true,cancelable:true}})
                ), 550);
              }}
            }}
          }};

          rec.onend = () => {{
            listening = false;
            btn.textContent = '';
            btn.classList.remove('listening');
            status.textContent = '';
            status.classList.remove('active');
          }};

          rec.onerror = (e) => {{
            listening = false;
            btn.textContent = '';
            btn.classList.remove('listening');
            status.textContent = e.error === 'not-allowed' ? '' : 'Warning: ';
            status.classList.remove('active');
          }};
          
          return true;
      }}

      if (!inject()) {{
        const interval = setInterval(() => {{
          if (inject()) clearInterval(interval);
        }}, 500);
        setTimeout(() => clearInterval(interval), 10000); // 10s max
      }}
    }})();
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

        with st.chat_message("assistant", avatar=""):
            with st.spinner(f"{t('thinking')} {lang_name}..."):
                response = ask_votebot(st.session_state["chat_session"], query)
            st.markdown(response)

            audio_data = None
            if audio_output:
                resp_lang = detect_language(response)
                with st.spinner(" Generating audio..."):
                    audio_data = text_to_speech(response, lang=resp_lang)
                if audio_data:
                    st.audio(audio_data, format="audio/mp3")

        st.session_state["messages"].append({"role": "assistant", "content": response, "audio": audio_data})
        st.rerun()

#  TAB 2: TIMELINE 
with tab_timeline:
    st.markdown(f"## {t('tab_timeline')}")

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
                st.markdown(f"<div style='text-align:right;'><small>{t('typical_duration_label')}</small><br><b>{phase['typical_duration']}</b></div>", unsafe_allow_html=True)

    st.divider()
    st.markdown("###  Types of Elections in India")
    etype_icons = ["🏛️", "🏘️", "📜", "🏙️", "🔄"]
    cols = st.columns(len(kb["election_types"]))
    for i, etype in enumerate(kb["election_types"]):
        with cols[i % len(cols)]:
            st.markdown(f"#### {etype_icons[i % len(etype_icons)]}\n**{etype['name']}**")
            st.caption(etype['description'])
            if "frequency" in etype:
                st.markdown(f" _{etype['frequency']}_")

#  TAB 3: ELIGIBILITY 
with tab_eligibility:
    st.markdown(f"## {t('tab_eligibility')}")

    st.info(f" **{t('smart_fill_info')}**")
    
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
            st.success(f" **{t('eligible_success')}**")
        else:
            st.error(f"(No) **{t('eligible_error')}**")
        for reason in result["reasons"]:
            st.markdown(f"- {reason}")
        if result["next_steps"]:
            st.markdown("** Next Steps:**")
            for i, step in enumerate(result["next_steps"], 1):
                st.markdown(f"{i}. {step}")

    st.divider()
    st.markdown(f"###  {t('alternate_ids_label')}")
    st.markdown(t('no_id_voting_info'))
    cols = st.columns(3)
    for i, id_doc in enumerate(kb["alternate_ids_for_voting"]):
        with cols[i % 3]:
            st.markdown(f"<span class='info-chip'>{id_doc}</span>", unsafe_allow_html=True)

#  TAB 4: CANDIDATES 
with tab_candidates:
    st.markdown(f"## {t('tab_candidates')}")
    st.info(f" {t('pincode_info')}")
    
    pincode = st.text_input(t('pincode_label'), placeholder="110001")
    
    if pincode:
        found_constituency = None
        for item in candidates_data:
            if pincode in item["pincodes"]:
                found_constituency = item
                break
        
        if found_constituency:
            st.success(f"{t('constituency_found')}: **{found_constituency['constituency']}, {found_constituency['state']}**")
            
            for cand in found_constituency["candidates"]:
                with st.expander(f" {t('affidavit_summary')}: {cand['name']}", expanded=True):
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

#  TAB 5: SIMULATOR 
with tab_simulator:
    st.markdown(f"## {t('tab_simulator')}")
    
    st.markdown("""
    <style>
    .sim-container {
        height: 320px; background: #ffffff; border-radius: 25px;
        display: flex; align-items: center; justify-content: center;
        border: 1px solid #f0f0f0; margin-bottom: 25px; position: relative;
        overflow: hidden; box-shadow: inset 0 0 20px rgba(0,0,0,0.02);
    }
    
    /* --- STEP 1: ZOOM MAP --- */
    .map-base {
        width: 150px; height: 150px; background: #e1f5fe; border-radius: 50%;
        position: relative; border: 5px solid #fff; box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        overflow: hidden; animation: zoomIn 3s infinite alternate;
    }
    .map-grid {
        background-image: radial-gradient(#81d4fa 1px, transparent 1px);
        background-size: 20px 20px; width: 100%; height: 100%;
    }
    .map-pin {
        position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
        font-size: 40px; filter: drop-shadow(0 5px 10px rgba(0,0,0,0.2));
    }
    @keyframes zoomIn {
        0% { transform: scale(0.8); }
        100% { transform: scale(1.4); }
    }

    /* --- STEP 2: DYNAMIC INKING --- */
    .finger-box { position: relative; height: 150px; width: 100px; display: flex; justify-content: center; align-items: flex-end; }
    .css-finger {
        width: 40px; height: 100px; background: #ffe0bd; border-radius: 20px 20px 5px 5px;
        border: 2px solid #e0c090; position: relative;
    }
    .css-nail {
        width: 24px; height: 30px; background: rgba(255,255,255,0.4);
        border-radius: 10px 10px 5px 5px; position: absolute; top: 8px; left: 50%; transform: translateX(-50%);
    }
    .finger-ink-tip {
        position: absolute; top: 0; left: 0; width: 100%; height: 25px;
        background: #6c5ce7; border-radius: 20px 20px 0 0; 
        opacity: 0; animation: inkApply 3s infinite; z-index: 2;
    }
    .ink-droplet {
        position: absolute; top: -60px; left: 50%; transform: translateX(-50%) rotate(45deg); 
        width: 12px; height: 12px; background: #6c5ce7; border-radius: 0 50% 50% 50%;
        animation: dropDown 3s infinite; z-index: 3;
    }
    @keyframes dropDown {
        0% { transform: translateY(0) translateX(-50%) rotate(45deg); opacity: 0; }
        30% { transform: translateY(60px) translateX(-50%) rotate(45deg); opacity: 1; }
        50%, 100% { transform: translateY(60px) translateX(-50%) rotate(45deg); opacity: 0; }
    }
    @keyframes inkApply {
        0%, 35% { opacity: 0; }
        50%, 100% { opacity: 1; }
    }

    /* --- STEP 4: VVPAT SLIP --- */
    .vvpat-box {
        width: 180px; height: 140px; background: #2c3e50; border-radius: 10px;
        position: relative; border: 4px solid #34495e; overflow: hidden;
    }
    .vvpat-window {
        width: 140px; height: 100px; background: #ecf0f1; margin: 15px auto;
        border-radius: 5px; position: relative; box-shadow: inset 0 5px 15px rgba(0,0,0,0.2);
    }
    .vvpat-slip {
        width: 100px; height: 70px; background: white; border: 1px solid #ddd;
        position: absolute; left: 20px; top: -80px;
        animation: slipFall 4s infinite; padding: 5px; box-sizing: border-box;
    }
    .vvpat-slip::after {
        content: ' (Done)'; font-family: sans-serif; font-size: 10px; color: #138808; font-weight: bold;
        display: block; text-align: center; margin-top: 15px;
    }
    @keyframes slipFall {
        0% { transform: translateY(0); }
        20% { transform: translateY(90px); }
        30% { transform: translateY(80px); }
        40% { transform: translateY(90px); }
        80%, 100% { transform: translateY(90px); opacity: 0; }
    }
    </style>
    """, unsafe_allow_html=True)

    if "sim_step" not in st.session_state:
        st.session_state["sim_step"] = 1
    
    progress_val = (st.session_state["sim_step"] - 1) / 3
    st.progress(progress_val)
    
    col_vis, col_text = st.columns([1, 1])
    
    if st.session_state["sim_step"] == 1:
        with col_vis:
            st.markdown('<div class="sim-container"><div class="map-base"><div class="map-grid"></div><div class="map-pin"></div></div></div>', unsafe_allow_html=True)
        with col_text:
            st.markdown(f"### {t('sim_step1_title')}")
            st.markdown(t("sim_step1_desc"))
            if st.button(t("sim_step1_btn"), use_container_width=True, type="primary"):
                st.session_state["sim_step"] = 2
                st.rerun()

    elif st.session_state["sim_step"] == 2:
        with col_vis:
            st.markdown('<div class="sim-container"><div class="finger-box"><div class="ink-droplet"></div><div class="css-finger"><div class="css-nail"></div><div class="finger-ink-tip"></div></div></div></div>', unsafe_allow_html=True)
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
            <div class="evm-container">
                <div class="evm-panel">
                    <div style="background:#34495e; height:40px; border-radius:6px; margin-bottom:12px; display:flex; align-items:center; padding:0 12px;">
                        <div class="evm-light"></div><span style="color:white; font-size:11px; margin-left:10px; font-family:sans-serif;">{t('evm_ready')}</span>
                    </div>
                    <div class="evm-row"><span style="font-size:10px; font-weight:bold;">{t('candidate')} A</span><button class="evm-btn"></button></div>
                    <div class="evm-row"><span style="font-size:10px; font-weight:bold;">{t('candidate')} B</span><button class="evm-btn"></button></div>
                    <div class="evm-row"><span style="font-size:10px; font-weight:bold;">NOTA</span><button class="evm-btn"></button></div>
                </div>
            </div>
            """
            st.components.v1.html(evm_html, height=320)
        with col_text:
            st.markdown(f"### {t('sim_step3_title')}")
            st.markdown(t("sim_step3_desc"))

            if st.button(t("vote_btn"), use_container_width=True, type="primary"):
                st.components.v1.html('<audio autoplay><source src="https://www.soundjay.com/buttons/beep-01a.mp3" type="audio/mpeg"></audio>', height=0)
                st.toast(t("vote_recorded"), icon="🗳️")
                import time
                time.sleep(1.5)
                st.session_state["sim_step"] = 4
                st.rerun()

    elif st.session_state["sim_step"] == 4:
        with col_vis:
            st.markdown('<div class="sim-container"><div class="vvpat-box"><div class="vvpat-window"><div class="vvpat-slip"></div></div></div></div>', unsafe_allow_html=True)
        with col_text:
            st.markdown(f"### {t('sim_step4_title')}")
            st.markdown(t("sim_step4_desc"))
            st.success(f" **{t('vote_verified')}**")

            
            if st.button(t("sim_reset"), use_container_width=True):
                st.session_state["sim_step"] = 1
                st.rerun()

#  TAB 6: VOTER GUIDE 
with tab_guide:
    st.markdown(f"##  {t('tab_guide')}")
    st.markdown(f"###  {t('reg_as_voter')}")
    reg = kb["voter_registration"]
    for i, step in enumerate(reg["steps"], 1):
        st.markdown(f"**{i}.** {step}")

    st.divider()
    st.markdown(f"### 📂 {t('docs_req')}")
    for doc in reg["documents_required"]:
        st.markdown(f"- {doc}")

    st.markdown(f"### ❓ {t('faqs_label')}")
    for faq in kb["faq"]:
        with st.expander(f"Q:  {faq['q']}"):
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
     VoteBot - Built for Hack2Skill PW Virtual Hackathon &nbsp;|&nbsp;
    Data source: Election Commission of India (ECI) &nbsp;|&nbsp;
    Powered by Google Gemini AI &nbsp;|&nbsp; Politically neutral. Always.
</div>
""", unsafe_allow_html=True)
