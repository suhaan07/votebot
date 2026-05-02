"""
app.py — VoteBot: India Election Assistant
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
from utils.llm import get_gemini_model, create_chat_session, ask_votebot, check_eligibility, translate_text

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

st.set_page_config(
    page_title="VoteBot — India Election Assistant",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

@st.cache_data
def load_kb():
    kb_path = Path(__file__).parent / "data" / "election_knowledge.json"
    with open(kb_path, "r") as f:
        return json.load(f)

kb = load_kb()

if "lang" not in st.session_state:
    st.session_state["lang"] = "en"

is_hindi = st.session_state["lang"] == "hi"

T = {
    "title": ("🗳️ VoteBot", "🗳️ वोटबॉट"),
    "subtitle": (
        "Your AI guide to India's Election Process — powered by Gemini & ECI data",
        "भारत की चुनाव प्रक्रिया का AI गाइड — Gemini और ECI डेटा द्वारा संचालित"
    ),
    "clear_chat": ("🗑️ Clear Chat", "🗑️ चैट साफ करें"),
    "tab_chat": ("💬 Ask VoteBot", "💬 वोटबॉट से पूछें"),
    "tab_timeline": ("📅 Election Timeline", "📅 चुनाव टाइमलाइन"),
    "tab_eligibility": ("✅ Am I Eligible?", "✅ क्या मैं पात्र हूं?"),
    "tab_guide": ("📖 Voter Guide", "📖 मतदाता गाइड"),
    "chat_placeholder": (
        "Ask about voter registration, election process, EVMs...",
        "मतदाता पंजीकरण, चुनाव प्रक्रिया के बारे में पूछें..."
    ),
    "welcome": (
        "Namaste! 🙏 I'm **VoteBot**, your guide to India's election process.\n\nI can help you with:\n- 🗂️ How to **register to vote**\n- 📋 Understanding the **election process** step by step\n- 🏛️ How **EVMs and VVPATs** work\n- 📜 The **Model Code of Conduct**\n- ✅ Checking **voter eligibility**\n\nAsk me anything about Indian elections! 🇮🇳",
        "नमस्ते! 🙏 मैं **वोटबॉट** हूं, भारत की चुनाव प्रक्रिया में आपका गाइड।\n\nमैं इनमें मदद कर सकता हूं:\n- 🗂️ **मतदाता पंजीकरण** कैसे करें\n- 📋 **चुनाव प्रक्रिया** को चरण-दर-चरण समझें\n- 🏛️ **EVM और VVPAT** कैसे काम करते हैं\n- 📜 **आदर्श आचार संहिता** क्या है\n- ✅ **मतदाता पात्रता** जांचें\n\nभारतीय चुनावों के बारे में कुछ भी पूछें! 🇮🇳"
    ),
    "quick_questions_en": [
        "How do I register to vote?",
        "What documents do I need to vote?",
        "What is the Model Code of Conduct?",
        "How does an EVM work?",
        "What is NOTA?",
        "How are election results counted?",
        "Who is eligible to stand as a candidate?",
        "What if my name is not on voter list?",
    ],
    "quick_questions_hi": [
        "मैं मतदाता पंजीकरण कैसे करूं?",
        "वोट देने के लिए कौन से दस्तावेज चाहिए?",
        "आदर्श आचार संहिता क्या है?",
        "EVM कैसे काम करती है?",
        "NOTA क्या है?",
        "चुनाव परिणाम कैसे गिने जाते हैं?",
        "उम्मीदवार बनने के लिए कौन पात्र है?",
        "अगर मेरा नाम मतदाता सूची में नहीं है?",
    ],
}

def t(key):
    idx = 1 if is_hindi else 0
    val = T[key]
    return val[idx] if isinstance(val, tuple) else val

def text_to_speech(text: str, lang: str = "en") -> bytes:
    try:
        from gtts import gTTS
        tts_lang = "hi" if lang == "hi" else "en"
        clean_text = text.replace("*", "").replace("#", "").replace("_", "").replace("💡", "").replace("🇮🇳", "")
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

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #FF9933 0%, #FFFFFF 50%, #138808 100%);
        padding: 1.5rem 2rem; border-radius: 12px;
        text-align: center; margin-bottom: 1rem;
    }
    .main-header h1 { color: #000080; font-size: 2.2rem; margin: 0; }
    .main-header p { color: #333; margin: 0.3rem 0 0 0; }
    .eligibility-box { border-radius: 10px; padding: 1rem; margin: 0.5rem 0; }
    .eligible { background: #d5f5e3; border: 1px solid #27ae60; }
    .not-eligible { background: #fadbd8; border: 1px solid #e74c3c; }
    .info-chip {
        display: inline-block; background: #f0f3ff;
        border: 1px solid #000080; color: #000080;
        border-radius: 20px; padding: 2px 10px; font-size: 0.8rem; margin: 2px;
    }
    .voice-box {
        background: #f8f0ff; border: 1px solid #8e44ad;
        border-radius: 10px; padding: 0.8rem 1rem; margin-bottom: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

col_title, col_lang = st.columns([5, 1])
with col_title:
    st.markdown(f"""
    <div class="main-header">
        <h1>{t("title")}</h1>
        <p>{t("subtitle")}</p>
    </div>
    """, unsafe_allow_html=True)
with col_lang:
    st.markdown("<br><br>", unsafe_allow_html=True)
    lang_label = "🇮🇳 हिंदी में बदलें" if not is_hindi else "🔤 Switch to English"
    if st.button(lang_label, key="lang_toggle", use_container_width=True):
        new_lang = "hi" if not is_hindi else "en"
        st.session_state["lang"] = new_lang
        
        if "messages" in st.session_state and st.session_state["messages"]:
            target_lang = "Hindi" if new_lang == "hi" else "English"
            model = st.session_state.get("model")
            if model:
                with st.spinner(f"Translating chat to {target_lang}... / चैट का अनुवाद हो रहा है..."):
                    error_occurred = False
                    try:
                        import time
                        for msg in st.session_state["messages"]:
                            msg["content"] = translate_text(model, msg["content"], target_lang)
                            if "audio" in msg:
                                msg.pop("audio")
                            time.sleep(0.5)  # Avoid rate limits
                    except Exception as e:
                        error_occurred = True
                        st.error(f"Translation failed: {e}")
                            
        if not locals().get("error_occurred", False):
            st.session_state["messages"] = list(st.session_state["messages"])
            # Rebuild chat session with translated history so Gemini doesn't bleed previous lang
            if "model" in st.session_state and "messages" in st.session_state:
                history = []
                for m in st.session_state["messages"]:
                    role = "model" if m["role"] == "assistant" else "user"
                    history.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))
                st.session_state["chat_session"] = create_chat_session(st.session_state["model"], history=history)
            else:
                st.session_state["chat_session"] = None
            st.rerun()

with st.sidebar:
    st.markdown("### 📚 Quick Topics / त्वरित विषय")
    questions = T["quick_questions_hi"] if is_hindi else T["quick_questions_en"]
    for q in questions:
        if st.button(q, key=f"quick_{q}", use_container_width=True):
            st.session_state["prefill_question"] = q

    st.divider()
    st.markdown("### 📞 Helplines")
    st.info("**Voter Helpline:** 1950\n\n**ECI Portal:** voters.eci.gov.in\n\n**MCC Violations:** cVIGIL App")

    st.divider()
    if st.button(t("clear_chat"), use_container_width=True):
        st.session_state["messages"] = []
        st.session_state["chat_session"] = None
        st.rerun()

tab_chat, tab_timeline, tab_eligibility, tab_guide = st.tabs([
    t("tab_chat"), t("tab_timeline"), t("tab_eligibility"), t("tab_guide")
])

# ── TAB 1: CHAT ───────────────────────────────────────────────────────────────
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

    # ── Compact inline mic — sits beside the Streamlit chat input bar ──────
    # Language for voice follows the UI toggle (is_hindi), not a separate radio.
    speech_lang_code = "hi-IN" if is_hindi else "en-IN"

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
                background: transparent;
                border: none;
                font-size: 1.25rem;
                cursor: pointer;
                padding: 4px 6px;
                border-radius: 50%;
                line-height: 1;
                transition: background 0.15s;
              }}
              #micBtn:hover {{ background: rgba(142,68,173,0.12); }}
              #micBtn.listening {{ animation: micpulse 0.9s infinite; }}
              @keyframes micpulse {{
                0%,100% {{ text-shadow: 0 0 0px #e74c3c; }}
                50%      {{ text-shadow: 0 0 8px #e74c3c; }}
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
          btn.textContent = '🎤';

          wrap.appendChild(status);
          wrap.appendChild(btn);
          chatInputContainer.appendChild(wrap);

          const SR = window.SpeechRecognition || window.webkitSpeechRecognition;

          if (!SR) {{
            btn.title = 'Speech not supported — use Chrome/Edge';
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
            btn.textContent = '⏹️';
            btn.classList.add('listening');
            status.textContent = '🔴';
            status.classList.add('active');
          }};

          rec.onresult = (e) => {{
            let interim = '', final = '';
            for (let i = e.resultIndex; i < e.results.length; i++) {{
              const tr = e.results[i][0].transcript;
              if (e.results[i].isFinal) final += tr; else interim += tr;
            }}
            status.textContent = final || interim ? '💬 ' + (final || interim).slice(0,24) + '…' : '🔴';
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
            btn.textContent = '🎤';
            btn.classList.remove('listening');
            status.textContent = '';
            status.classList.remove('active');
          }};

          rec.onerror = (e) => {{
            listening = false;
            btn.textContent = '🎤';
            btn.classList.remove('listening');
            status.textContent = e.error === 'not-allowed' ? '🔒' : '⚠️';
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

    audio_output = st.toggle("🔊 Read responses aloud / जवाब सुनें", value=False, key="audio_toggle")

    for msg in st.session_state["messages"]:
        avatar = "🗳️" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and audio_output and msg.get("audio"):
                st.audio(msg["audio"], format="audio/mp3")

    prefill = st.session_state.pop("prefill_question", None)
    user_input = st.chat_input(t("chat_placeholder")) or prefill

    # Render mic button script (invisible iframe)
    st.components.v1.html(mic_html, height=0)

    if user_input:
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
        st.session_state["messages"].append({"role": "user", "content": user_input})

        # Language logic:
        # UI language (toggle) takes full priority.
        # Hindi UI → always respond in Hindi, regardless of input script.
        # English UI → always respond in English, regardless of input script.
        if is_hindi:
            query = f"कृपया हिंदी में जवाब दें (respond only in Hindi): {user_input}"
        else:
            query = f"Please respond in English only: {user_input}"

        with st.chat_message("assistant", avatar="🗳️"):
            with st.spinner("VoteBot सोच रहा है..." if is_hindi else "VoteBot is thinking..."):
                response = ask_votebot(st.session_state["chat_session"], query)
            st.markdown(response)

            audio_data = None
            if audio_output:
                resp_lang = detect_language(response)
                with st.spinner("🔊 Generating audio..."):
                    audio_data = text_to_speech(response, lang=resp_lang)
                if audio_data:
                    st.audio(audio_data, format="audio/mp3")

        st.session_state["messages"].append({"role": "assistant", "content": response, "audio": audio_data})
        st.rerun()

# ── TAB 2: TIMELINE ───────────────────────────────────────────────────────────
with tab_timeline:
    if is_hindi:
        st.markdown("## 📅 भारतीय चुनाव — 8 चरण")
    else:
        st.markdown("## 📅 How an Indian Election Works — Step by Step")

    phases = kb["election_process_phases"]
    phase_icons = ["📢", "📝", "🔍", "🚪", "📣", "🗳️", "🔢", "🏛️"]
    for i, phase in enumerate(phases):
        with st.expander(f"{phase_icons[i]} Phase {phase['phase']}: {phase['name']}", expanded=(i == 0)):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{phase['description']}**")
                st.markdown("**Key Events:**")
                for event in phase["key_events"]:
                    st.markdown(f"- {event}")
            with col2:
                st.metric("Typical Duration", phase["typical_duration"])

    st.divider()
    st.markdown("### 🏛️ Types of Elections in India")
    cols = st.columns(len(kb["election_types"]))
    for i, etype in enumerate(kb["election_types"]):
        with cols[i % len(cols)]:
            st.markdown(f"**{etype['name']}**")
            st.caption(etype['description'])
            if "frequency" in etype:
                st.markdown(f"🔄 _{etype['frequency']}_")

# ── TAB 3: ELIGIBILITY ────────────────────────────────────────────────────────
with tab_eligibility:
    if is_hindi:
        st.markdown("## ✅ क्या मैं वोट देने के लिए पात्र हूं?")
    else:
        st.markdown("## ✅ Am I Eligible to Vote?")

    with st.form("eligibility_form"):
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("आपकी उम्र / Your Age", min_value=1, max_value=120, value=20)
            is_citizen = st.radio("भारतीय नागरिक? / Indian citizen?", ["Yes / हाँ", "No / नहीं"]) == "Yes / हाँ"
        with col2:
            is_resident = st.radio("भारत में निवास? / Resident in India?", ["Yes / हाँ", "No / नहीं (NRI)"]) == "Yes / हाँ"
            disqualified = st.checkbox("अदालत द्वारा अयोग्य / Court disqualification or 2+ yr sentence", value=False)
        submitted = st.form_submit_button("जांचें / Check Eligibility →", use_container_width=True)

    if submitted:
        result = check_eligibility(age, is_citizen, is_resident, disqualified)
        if result["eligible"]:
            st.success("🎉 **You are eligible to vote! / आप वोट देने के पात्र हैं!**")
        else:
            st.error("❌ **You may not be eligible. / आप पात्र नहीं हो सकते।**")
        for reason in result["reasons"]:
            st.markdown(f"- {reason}")
        if result["next_steps"]:
            st.markdown("**📋 Next Steps:**")
            for i, step in enumerate(result["next_steps"], 1):
                st.markdown(f"{i}. {step}")

    st.divider()
    st.markdown("### 🪪 Alternate IDs Accepted at Polling Booth")
    st.markdown("You can vote even without a Voter ID card if your **name is on the electoral roll** and you carry any ONE of these:")
    cols = st.columns(3)
    for i, id_doc in enumerate(kb["alternate_ids_for_voting"]):
        with cols[i % 3]:
            st.markdown(f"<span class='info-chip'>{id_doc}</span>", unsafe_allow_html=True)

# ── TAB 4: VOTER GUIDE ────────────────────────────────────────────────────────
with tab_guide:
    st.markdown("## 📖 Complete Voter Guide / संपूर्ण मतदाता गाइड")
    st.markdown("### 📝 How to Register as a Voter")
    reg = kb["voter_registration"]
    for i, step in enumerate(reg["steps"], 1):
        st.markdown(f"**{i}.** {step}")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📄 Documents Required")
        for doc in reg["documents_required"]:
            st.markdown(f"- {doc}")
    with col2:
        st.markdown("### 🌐 Registration Links")
        st.markdown(f"- **Voter Portal:** [voters.eci.gov.in]({reg['online_portal']})")
        st.markdown(f"- **ECI Website:** [eci.gov.in]({kb['important_helplines']['eci_website']})")
        st.markdown(f"- **Voter Helpline:** {reg['app']}")
        st.markdown(f"- **Report Violations:** {kb['important_helplines']['cvigil_app']}")

    st.divider()
    st.markdown("### 🤔 Frequently Asked Questions / अक्सर पूछे जाने वाले सवाल")
    for faq in kb["faq"]:
        with st.expander(f"❓ {faq['q']}"):
            st.markdown(faq["a"])

    st.divider()
    st.markdown("### 👥 Key Election Officials")
    cols = st.columns(2)
    for i, official in enumerate(kb["key_officials"]):
        with cols[i % 2]:
            st.markdown(f"**🏛️ {official['role']}**")
            st.caption(official["responsibility"])

    st.divider()
    st.markdown("### 📜 Model Code of Conduct — Key Rules")
    mcc = kb["model_code_of_conduct"]
    st.markdown(f"_{mcc['description']}_")
    for rule in mcc["key_rules"]:
        st.markdown(f"- {rule}")
    st.caption(f"Enforcement: {mcc['enforcement']}")

st.divider()
st.markdown("""
<div style='text-align: center; color: #888; font-size: 0.8rem;'>
    🇮🇳 VoteBot — Built for Hack2Skill PW Virtual Hackathon &nbsp;|&nbsp;
    Data source: Election Commission of India (ECI) &nbsp;|&nbsp;
    Powered by Google Gemini AI &nbsp;|&nbsp; Politically neutral. Always.
</div>
""", unsafe_allow_html=True)
