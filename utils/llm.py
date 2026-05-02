import json
import os
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv()

_KB_PATH = Path(__file__).parent.parent / "data" / "election_knowledge.json"

def _load_knowledge() -> str:
    with open(_KB_PATH, "r", encoding="utf-8") as f:
        return json.dumps(json.load(f), indent=2)

KNOWLEDGE_BASE = _load_knowledge()

SYSTEM_PROMPT = f"""You are "VoteBot", a friendly and neutral assistant that helps Indian citizens 
understand the election process governed by the Election Commission of India (ECI).

KNOWLEDGE BASE:
{KNOWLEDGE_BASE}

GUIDELINES:
1. Be simple and clear — your users may be first-time voters.
2. Always be politically NEUTRAL. Never favour any party or candidate.
3. Use numbered steps when explaining a process.
4. End responses with: "💡 You might also want to know:" and suggest a follow-up question.
5. Keep answers under 250 words unless asked for more detail.
6. Support both Hindi and English questions.
"""

def get_gemini_model():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set.")
    return genai.Client(api_key=api_key)

def create_chat_session(client, history=None):
    return client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3,
            max_output_tokens=600,
        ),
        history=history
    )

def ask_votebot(chat_session, user_message: str) -> str:
    try:
        response = chat_session.send_message(user_message)
        return response.text
    except Exception as e:
        return f"⚠️ Sorry, I ran into an issue: {str(e)}. Please try again."

def translate_text(client, text: str, target_lang: str) -> str:
    prompt = f"Translate the following text to {target_lang}. Preserve all markdown formatting, emojis, and structure. Only output the translated text:\n\n{text}"
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        raise e

def check_eligibility(age: int, is_citizen: bool, is_resident: bool, disqualified: bool) -> dict:
    reasons = []
    next_steps = []
    eligible = True

    if age < 18:
        eligible = False
        reasons.append(f"❌ You must be at least 18 years old. You are {age}.")
        next_steps.append("You can register as a voter when you turn 18.")
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
        reasons.append("❌ You have indicated a disqualification.")

    if eligible:
        next_steps = [
            "Visit voters.eci.gov.in to check if your name is on the electoral roll.",
            "If not registered, fill Form 6 online — takes under 10 minutes.",
            "Keep your Aadhaar and proof of residence handy.",
            "Call 1950 (Voter Helpline) if you need assistance.",
        ]

    return {"eligible": eligible, "reasons": reasons, "next_steps": next_steps}