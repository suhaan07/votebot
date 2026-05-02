"""
llm.py — Gemini-powered election assistant backend
Loads the election knowledge base and injects it as context into every Gemini call.
"""

import json
import os
import google.generativeai as genai
from pathlib import Path

# ── Load knowledge base once at import time ──────────────────────────────────
_KB_PATH = Path(__file__).parent.parent / "data" / "election_knowledge.json"

def _load_knowledge() -> str:
    with open(_KB_PATH, "r", encoding="utf-8") as f:
        kb = json.load(f)
    return json.dumps(kb, indent=2)

KNOWLEDGE_BASE = _load_knowledge()

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are "VoteBot", an expert, friendly, and neutral assistant that helps Indian citizens 
understand the election process governed by the Election Commission of India (ECI).

You have deep knowledge of:
- How to register as a voter
- The complete election process from announcement to government formation
- Voter ID (EPIC), EVMs, VVPAT, NOTA
- Model Code of Conduct
- Key officials and their roles
- Voter eligibility and disqualifications
- Important helplines and portals

KNOWLEDGE BASE (always refer to this):
{KNOWLEDGE_BASE}

GUIDELINES:
1. Be simple, clear, and friendly — your users may be first-time voters.
2. Always be politically NEUTRAL. Never favour any party, candidate, or ideology.
3. If a user asks about a specific candidate or party's views, politely decline and redirect to process questions.
4. Use numbered steps when explaining a process.
5. At the end of your response, suggest 1 follow-up question the user might want to ask (prefix with "💡 You might also want to know:").
6. If a question is outside Indian elections, politely say so and offer to help with election-related queries.
7. Respond in the same language the user writes in (Hindi or English). If Hindi, use simple Hinglish if needed.
8. Keep answers concise (under 250 words) unless the user explicitly asks for more detail.
"""

# ── Gemini client setup ───────────────────────────────────────────────────────
def get_gemini_model():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in environment variables.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT,
        generation_config=genai.GenerationConfig(
            temperature=0.3,       # Low temp = factual, consistent answers
            max_output_tokens=600,
        )
    )

# ── Chat session manager ──────────────────────────────────────────────────────
def create_chat_session(model):
    """Start a fresh multi-turn chat session."""
    return model.start_chat(history=[])

def ask_votebot(chat_session, user_message: str) -> str:
    """Send a message and get a response from VoteBot."""
    try:
        response = chat_session.send_message(user_message)
        return response.text
    except Exception as e:
        return f"⚠️ Sorry, I ran into an issue: {str(e)}. Please try again."

# ── Eligibility checker ───────────────────────────────────────────────────────
def check_eligibility(age: int, is_citizen: bool, is_resident: bool, disqualified: bool) -> dict:
    """
    Rule-based eligibility check (no LLM needed — deterministic).
    Returns a dict with eligible (bool), reasons (list), and next_steps (list).
    """
    reasons = []
    next_steps = []
    eligible = True

    if age < 18:
        eligible = False
        reasons.append(f"❌ You must be at least 18 years old. You are {age}.")
        next_steps.append(f"You can register as a voter when you turn 18.")
    else:
        reasons.append(f"✅ Age {age} — meets the minimum age requirement of 18.")

    if not is_citizen:
        eligible = False
        reasons.append("❌ Only Indian citizens can vote in Indian elections.")
    else:
        reasons.append("✅ Indian citizenship confirmed.")

    if not is_resident:
        eligible = False
        reasons.append("❌ You must be ordinarily resident in the constituency to register.")
        next_steps.append("NRIs can register as overseas electors via Form 6A at voters.eci.gov.in.")
    else:
        reasons.append("✅ Resident in the constituency.")

    if disqualified:
        eligible = False
        reasons.append("❌ You have indicated a disqualification (e.g., court-declared unsound mind or imprisonment).")
    
    if eligible:
        next_steps = [
            "Visit voters.eci.gov.in to check if your name is already on the electoral roll.",
            "If not registered, fill Form 6 online — takes under 10 minutes.",
            "Keep your Aadhaar and a proof of residence handy.",
            "Call 1950 (Voter Helpline) if you need assistance.",
        ]

    return {
        "eligible": eligible,
        "reasons": reasons,
        "next_steps": next_steps,
    }
