# 🗳️ VoterMitra - Your Digital Election Companion

> **VoterMitra** is an advanced, AI-powered assistant designed to empower 96.8 crore Indian citizens with accurate, multilingual, and interactive election knowledge. Built with **Google Gemini 1.5 Flash**, it bridges the gap between complex ECI procedures and every voter.

---

## 🏛️ Project Overview
**VoterMitra** was built for the **Hack2Skill PW Virtual Hackathon** under the **Civic Education & Election Awareness** vertical. It serves as a one-stop portal for understanding voter registration, election phases, candidate backgrounds, and the voting process through immersive simulations.

### 🌟 Key Features (The "Wow" Factor)

| Feature | Description | Tech Highlight |
|---|---|---|
| **🌐 Full Multilingual Support** | Instant UI & Chat switching between **English, Hindi, Bengali, Marathi, and Tamil**. | Deep-sync Translation Engine |
| **🎙️ Voice-First Interaction** | Users can speak their questions in Hindi or English and hear the AI respond back. | gTTS + SpeechRecognition |
| **🎮 Voting Booth Simulator** | A step-by-step interactive 2D simulation of the polling station experience. | CSS Animations + Logic |
| **🆔 Smart Eligibility Scan** | Scan your ID card to automatically extract age and check voting eligibility. | Gemini Vision OCR |
| **🔍 Candidate Affidavit AI** | Instant summaries of candidate assets, education, and criminal records from pincodes. | AI Summarization |
| **📅 Interactive Timeline** | 8-phase breakdown of the election process with milestone tracking. | ECI Phase Logic |
| **📜 MCC & FAQ Hub** | Dynamic access to Model Code of Conduct rules and common voter queries. | Structured KB Injection |
| **🌐 Google Ecosystem & a11y** | Native Google Calendar reminders, Google Maps integration, and fully ARIA-compliant accessible UI. | Google APIs + a11y Standards |

---

## 🧠 Architecture & Approach

### 1. Knowledge Base Grounding (RAG-Lite)
Instead of relying on general LLM knowledge, **VoterMitra** is grounded in a structured ECI Knowledge Base. Every response is verified against official ECI Handbooks provided in the system context.

### 2. Multi-Modal Vision
The "Eligibility Check" uses Gemini's multi-modal capabilities to analyze uploaded documents (ID cards) and extract relevant data, making the process friction-less for users.

### 3. State-of-the-Art Multilingual Engine
We implemented a custom synchronization layer that ensures all UI icons, buttons, and "Smart Tips" are perfectly mirrored across all 5 languages, maintaining a premium look in every regional script.

---

## 🛠️ Tech Stack
- **Core Engine**: Streamlit (Python)
- **AI Brain**: Google Gemini 1.5 Flash (via Google GenAI SDK)
- **Speech**: Google Text-to-Speech (gTTS) & Web Speech API
- **OCR/Vision**: Gemini 1.5 Multi-modal
- **Design**: Vanilla CSS with Indian Tricolor Branding

---

## 🚀 Setup & Running Locally

### Prerequisites
- Python 3.10+
- A Google Gemini API key from [AI Studio](https://aistudio.google.com)

### Installation
```bash
# 1. Clone the repository
git clone https://github.com/suhaan07/votebot.git
cd votebot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
echo "GEMINI_API_KEY=your_key_here" > .env

# 4. Launch VoterMitra
streamlit run app.py
```

---

## 🛡️ Security & Neutrality
- **Politically Neutral**: Hardcoded system instructions ensure the AI never favors any political party or candidate.
- **Privacy First**: No user data or uploaded ID images are stored on our servers.
- **API Security**: Key management via `.env` and streamlit secrets.

---

## 🇮🇳 Built for India
Data source: [Election Commission of India (ECI)](https://eci.gov.in) | Developed for the Hack2Skill PW Virtual Hackathon.

---

## 🏗️ Technical Architecture & Logic

### Detailed System Flow
```
User (Streamlit UI)
    │
    ├─► [6 Tabs: Chat | Timeline | Eligibility | Candidates | Simulator | Guide]
    │
    ├─► Gemini 1.5 Flash API (with Custom System Prompt)
    │    └─► RAG-Lite: ECI Knowledge Base Injection (JSON)
    │
    ├─► Multilingual Engine
    │    └─► Dynamic UI Mapping (EN, HI, BN, MR, TA)
    │
    └─► Deterministic Engines
         ├─► Rule-based Eligibility Logic
         └─► CSS-based Voting Simulation
```

### Key Implementation Details
1. **Low Latency & Factual Accuracy**: Gemini is configured with a **Temperature of 0.3**. This ensures that election process information remains consistent and avoids hallucinations, which is critical for a civic education tool.
2. **Vision Integration**: We utilize the `gemini-1.5-flash` model to perform OCR on identity documents. This allows for an automated "Smart Fill" of the eligibility form.
3. **Audio Pipeline**:
    - **Inbound**: SpeechRecognition library processes mic input to text.
    - **Outbound**: gTTS converts AI text to high-quality Hindi/English audio.
4. **Data Structure**: Candidates and Knowledge Base are stored in hierarchical JSON files, allowing for rapid lookups by pincode or topic without expensive database overhead.

---

## 📂 Project Structure
```
votebot/
├── app.py                  # Main Entry Point (Streamlit UI & Logic)
├── requirements.txt        # Python Dependencies
├── .env                    # Environment Variables (Secrets)
├── data/
│   ├── election_knowledge.json    # Core ECI Knowledge Base
│   └── candidates.json            # Candidate Profiles & Pincode Mapping
├── utils/
│   ├── llm.py              # Gemini Client & Eligibility Logic
│   └── translations.py     # Multilingual Master Dictionary
└── scratch/                # Maintenance & Syncing Scripts
```

---

## 📋 Evaluation Criteria Addressed

| Criterion | How Addressed |
|---|---|
| **Code Quality** | Clean, modular separation of UI (`app.py`), Logic (`llm.py`), and Data (`data/`). |
| **User Experience** | Immersive 2D simulator and voice interaction for maximum accessibility. |
| **Efficiency** | Cached data loading with `@st.cache_data` for near-instant UI responses. |
| **Security** | Secrets managed via `.env`, no persistent storage of PII. |
| **Innovation** | Combined LLM chat with deterministic simulations for a hybrid education model. |
| **Scalability** | Translation engine designed to support additional languages (e.g., Telugu, Kannada) by simply adding JSON keys. |

---

## 📝 Assumptions & Scope
1. **Target Audience**: Primarily first-time and youth voters in India.
2. **Data Recency**: Knowledge base is aligned with ECI guidelines for the 2024 General Elections.
3. **Accessibility**: Focused on visual and audio-based learning to assist users with varying literacy levels.
4. **Neutrality**: Built-in guardrails to ensure the assistant remains a neutral "Digital India" tool.
