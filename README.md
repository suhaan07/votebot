# 🗳️ VoteBot — India Election Assistant

> An AI-powered assistant that helps Indian citizens understand the election process, voter registration, timelines, and their rights — built with Google Gemini and Streamlit.

---

## 🎯 Chosen Vertical

**Civic Education & Election Awareness** — Helping Indian citizens navigate the complete election process governed by the Election Commission of India (ECI), from voter registration to result declaration.

---

## 🧠 Approach & Logic

### Architecture

```
User (Streamlit UI)
    │
    ▼
[4 Tabs: Chat | Timeline | Eligibility | Voter Guide]
    │
    ├── Gemini 1.5 Flash API  ←  System Prompt + ECI Knowledge Base (JSON)
    │       └── Multi-turn chat with election persona "VoteBot"
    │
    ├── Rule-based Eligibility Engine (no LLM — deterministic)
    │
    └── Static Knowledge Base (data/election_knowledge.json)
```

### Key Design Decisions

1. **Knowledge Base Injection**: Instead of relying on Gemini's general knowledge (which may be outdated), we inject a structured JSON knowledge base of ECI data into the system prompt. This ensures accurate, up-to-date answers.

2. **Low Temperature (0.3)**: Gemini is configured with low temperature for factual consistency — election process information should not hallucinate.

3. **Deterministic Eligibility Checker**: Voter eligibility is rule-based (age ≥ 18, citizenship, residency, no disqualifications) — we don't use an LLM for this because the rules are fixed by law.

4. **Political Neutrality**: The system prompt explicitly instructs VoteBot to never favour any party, candidate, or ideology.

5. **Multi-turn Memory**: Gemini's `start_chat()` maintains conversation history, so users can ask follow-up questions naturally.

---

## 🔧 How the Solution Works

### Features

| Feature | Description |
|---|---|
| 💬 **AI Chatbot** | Ask any question about Indian elections in plain English or Hindi |
| 📅 **Election Timeline** | Visual, expandable 8-phase breakdown from announcement to government formation |
| ✅ **Eligibility Checker** | Rule-based form to check if you can vote, with personalised next steps |
| 📖 **Voter Guide** | Step-by-step registration guide, FAQs, key officials, MCC rules |
| 🎯 **Quick Topics** | One-click sidebar buttons for common questions |

### Google Services Used

- **Google Gemini 1.5 Flash** — Core LLM powering the conversational assistant
- **Google AI Studio** — API key management

---

## 🚀 Setup & Running Locally

### Prerequisites

- Python 3.10+
- A free Gemini API key from [aistudio.google.com](https://aistudio.google.com)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/election-assistant.git
cd election-assistant

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your API key
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 4. Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`

### API Key (in-app)
You can also enter your Gemini API key directly in the app's sidebar — no `.env` file needed.

---

## 📁 Project Structure

```
election-assistant/
├── app.py                        # Main Streamlit application
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variable template
├── .gitignore
├── .streamlit/
│   └── config.toml               # Streamlit theme (Indian flag colours)
├── data/
│   └── election_knowledge.json   # Structured ECI knowledge base
└── utils/
    └── llm.py                    # Gemini API client + eligibility logic
```

---

## 💡 Assumptions Made

1. The app targets Indian general public, especially first-time voters.
2. Data is based on ECI guidelines as of 2024 Lok Sabha elections.
3. Users have internet access to reach the Gemini API.
4. The app is politically neutral and does not provide opinions on parties or candidates.
5. NRI voters are acknowledged (Form 6A) but in-person voting is noted as required.

---

## 🔒 Security

- API keys are never hardcoded — entered via UI or `.env` file (excluded from git)
- No user data is stored or logged
- Gemini API calls are stateless (only session-level history)

---

## 📊 Evaluation Criteria Addressed

| Criterion | How Addressed |
|---|---|
| **Code Quality** | Modular structure: `app.py`, `utils/llm.py`, `data/` separated |
| **Security** | API keys via env vars / UI input, `.gitignore` for secrets |
| **Efficiency** | Knowledge base cached with `@st.cache_data`; low-token Gemini responses |
| **Testing** | Deterministic eligibility checker is unit-testable; chatbot covers FAQ edge cases |
| **Accessibility** | Simple language, Hindi support, helpline numbers, 12 alternate voter IDs listed |
| **Google Services** | Gemini 1.5 Flash as core LLM; Google AI Studio for key management |

---

## 🇮🇳 Built for Hack2Skill PW Virtual Hackathon

Data source: [Election Commission of India](https://eci.gov.in) | Powered by Google Gemini AI
