"""
app.py — VoteBot: India Election Assistant
A Streamlit app powered by Gemini that helps Indian citizens understand the election process.
"""

import streamlit as st
import json
from pathlib import Path
from utils.llm import get_gemini_model, create_chat_session, ask_votebot, check_eligibility

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VoteBot — India Election Assistant",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load knowledge base ───────────────────────────────────────────────────────
@st.cache_data
def load_kb():
    kb_path = Path(__file__).parent / "data" / "election_knowledge.json"
    with open(kb_path, "r") as f:
        return json.load(f)

kb = load_kb()

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #FF9933 0%, #FFFFFF 50%, #138808 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 1rem;
    }
    .main-header h1 { color: #000080; font-size: 2.2rem; margin: 0; }
    .main-header p { color: #333; margin: 0.3rem 0 0 0; }
    .phase-card {
        border-left: 4px solid #FF9933;
        background: #fff8f0;
        padding: 0.8rem 1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 0.6rem;
    }
    .phase-number {
        font-size: 0.75rem;
        font-weight: bold;
        color: #FF9933;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .phase-title { font-weight: bold; color: #000080; font-size: 1rem; }
    .chat-tip {
        background: #e8f4fd;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        font-size: 0.85rem;
        color: #1a5276;
        margin-bottom: 0.5rem;
        cursor: pointer;
    }
    .eligibility-box {
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .eligible { background: #d5f5e3; border: 1px solid #27ae60; }
    .not-eligible { background: #fadbd8; border: 1px solid #e74c3c; }
    .info-chip {
        display: inline-block;
        background: #f0f3ff;
        border: 1px solid #000080;
        color: #000080;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.8rem;
        margin: 2px;
    }
    div[data-testid="stChatMessage"] { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🗳️ VoteBot</h1>
    <p>Your AI guide to India's Election Process — powered by Gemini & ECI data</p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Setup")
    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        placeholder="AIza...",
        help="Get your free key at aistudio.google.com",
    )
    if api_key:
        import os
        os.environ["GEMINI_API_KEY"] = api_key

    st.divider()
    st.markdown("### 📚 Quick Topics")
    quick_questions = [
        "How do I register to vote?",
        "What documents do I need to vote?",
        "What is the Model Code of Conduct?",
        "How does an EVM work?",
        "What is NOTA?",
        "How are election results counted?",
        "Who is eligible to stand as a candidate?",
        "What happens if my name is not on voter list?",
    ]
    for q in quick_questions:
        if st.button(q, key=f"quick_{q}", use_container_width=True):
            st.session_state["prefill_question"] = q

    st.divider()
    st.markdown("### 📞 Helplines")
    st.info("**Voter Helpline:** 1950\n\n**ECI Portal:** voters.eci.gov.in\n\n**MCC Violations:** cVIGIL App")

    st.divider()
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state["messages"] = []
        st.session_state["chat_session"] = None
        st.rerun()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_chat, tab_timeline, tab_eligibility, tab_guide = st.tabs([
    "💬 Ask VoteBot", "📅 Election Timeline", "✅ Am I Eligible?", "📖 Voter Guide"
])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — CHAT
# ════════════════════════════════════════════════════════════════════════════
with tab_chat:
    if not api_key:
        st.warning("👈 Please enter your **Gemini API Key** in the sidebar to start chatting.")
        st.markdown("""
        **How to get a free Gemini API key:**
        1. Go to [aistudio.google.com](https://aistudio.google.com)
        2. Sign in with your Google account
        3. Click **"Get API Key"**
        4. Paste it in the sidebar above
        """)
    else:
        # Init model and session
        if "model" not in st.session_state:
            try:
                st.session_state["model"] = get_gemini_model()
            except Exception as e:
                st.error(f"Could not connect to Gemini: {e}")
                st.stop()

        if "chat_session" not in st.session_state or st.session_state["chat_session"] is None:
            st.session_state["chat_session"] = create_chat_session(st.session_state["model"])

        if "messages" not in st.session_state:
            st.session_state["messages"] = []

        # Welcome message
        if not st.session_state["messages"]:
            with st.chat_message("assistant", avatar="🗳️"):
                st.markdown("""
Namaste! 🙏 I'm **VoteBot**, your guide to India's election process.

I can help you with:
- 🗂️ How to **register to vote** (Form 6, documents needed)
- 📋 Understanding the **election process** step by step
- 🏛️ How **EVMs and VVPATs** work
- 📜 The **Model Code of Conduct**
- ✅ Checking **voter eligibility**
- 📍 Finding your **polling booth**

Ask me anything about Indian elections! 🇮🇳
                """)

        # Display chat history
        for msg in st.session_state["messages"]:
            avatar = "🗳️" if msg["role"] == "assistant" else "👤"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

        # Handle prefilled question from sidebar
        prefill = st.session_state.pop("prefill_question", None)

        # Chat input
        user_input = st.chat_input("Ask about voter registration, election process, EVMs...") or prefill

        if user_input:
            # Show user message
            with st.chat_message("user", avatar="👤"):
                st.markdown(user_input)
            st.session_state["messages"].append({"role": "user", "content": user_input})

            # Get and show assistant response
            with st.chat_message("assistant", avatar="🗳️"):
                with st.spinner("VoteBot is thinking..."):
                    response = ask_votebot(st.session_state["chat_session"], user_input)
                st.markdown(response)
            st.session_state["messages"].append({"role": "assistant", "content": response})
            st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — ELECTION TIMELINE
# ════════════════════════════════════════════════════════════════════════════
with tab_timeline:
    st.markdown("## 📅 How an Indian Election Works — Step by Step")
    st.markdown("From the announcement of dates to the formation of government, here are the **8 phases** of an Indian election:")

    phases = kb["election_process_phases"]
    phase_colors = ["#FF9933", "#e67e22", "#d35400", "#c0392b", "#8e44ad", "#2980b9", "#27ae60", "#138808"]
    phase_icons = ["📢", "📝", "🔍", "🚪", "📣", "🗳️", "🔢", "🏛️"]

    for i, phase in enumerate(phases):
        color = phase_colors[i % len(phase_colors)]
        icon = phase_icons[i]
        with st.expander(f"{icon} Phase {phase['phase']}: {phase['name']}", expanded=(i == 0)):
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

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — ELIGIBILITY CHECKER
# ════════════════════════════════════════════════════════════════════════════
with tab_eligibility:
    st.markdown("## ✅ Am I Eligible to Vote?")
    st.markdown("Answer a few quick questions to find out if you can vote in Indian elections.")

    with st.form("eligibility_form"):
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Your Age", min_value=1, max_value=120, value=20, step=1)
            is_citizen = st.radio("Are you an Indian citizen?", ["Yes", "No"]) == "Yes"
        with col2:
            is_resident = st.radio(
                "Are you ordinarily resident in an Indian constituency?",
                ["Yes", "No (NRI / Abroad)"]
            ) == "Yes"
            disqualified = st.checkbox(
                "I have been declared of unsound mind by a court, OR I am serving 2+ years imprisonment",
                value=False
            )

        submitted = st.form_submit_button("Check My Eligibility →", use_container_width=True)

    if submitted:
        result = check_eligibility(age, is_citizen, is_resident, disqualified)
        if result["eligible"]:
            st.markdown('<div class="eligibility-box eligible">', unsafe_allow_html=True)
            st.success("🎉 **You are eligible to vote in Indian elections!**")
        else:
            st.markdown('<div class="eligibility-box not-eligible">', unsafe_allow_html=True)
            st.error("❌ **You may not be eligible to vote at this time.**")

        st.markdown("**Your eligibility check results:**")
        for reason in result["reasons"]:
            st.markdown(f"- {reason}")

        if result["next_steps"]:
            st.markdown("**📋 Next Steps:**")
            for i, step in enumerate(result["next_steps"], 1):
                st.markdown(f"{i}. {step}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    st.markdown("### 🪪 Alternate IDs Accepted at Polling Booth")
    st.markdown("You can vote even without a Voter ID card if your **name is on the electoral roll** and you carry any ONE of these:")
    ids = kb["alternate_ids_for_voting"]
    cols = st.columns(3)
    for i, id_doc in enumerate(ids):
        with cols[i % 3]:
            st.markdown(f"<span class='info-chip'>{id_doc}</span>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — VOTER GUIDE
# ════════════════════════════════════════════════════════════════════════════
with tab_guide:
    st.markdown("## 📖 Complete Voter Guide")

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
    st.markdown("### 🤔 Frequently Asked Questions")
    for faq in kb["faq"]:
        with st.expander(f"❓ {faq['q']}"):
            st.markdown(faq["a"])

    st.divider()
    st.markdown("### 👥 Key Election Officials")
    officials = kb["key_officials"]
    cols = st.columns(2)
    for i, official in enumerate(officials):
        with cols[i % 2]:
            st.markdown(f"**🏛️ {official['role']}**")
            st.caption(official["responsibility"])
            st.markdown("")

    st.divider()
    st.markdown("### 📜 Model Code of Conduct — Key Rules")
    mcc = kb["model_code_of_conduct"]
    st.markdown(f"_{mcc['description']}_")
    for rule in mcc["key_rules"]:
        st.markdown(f"- {rule}")
    st.caption(f"Enforcement: {mcc['enforcement']}")

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown("""
<div style='text-align: center; color: #888; font-size: 0.8rem;'>
    🇮🇳 VoteBot — Built for Hack2Skill PW Virtual Hackathon &nbsp;|&nbsp; 
    Data source: Election Commission of India (ECI) &nbsp;|&nbsp;
    Powered by Google Gemini AI &nbsp;|&nbsp;
    Politically neutral. Always.
</div>
""", unsafe_allow_html=True)
