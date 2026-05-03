import json
import os
from pathlib import Path
from google import genai
from google.genai import types
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

def get_system_prompt(kb_data) -> str:
    kb_str = json.dumps(kb_data, indent=2)
    return f"""You are "VoterMitra", a friendly and neutral assistant that helps Indian citizens 
understand the election process governed by the Election Commission of India (ECI).

KNOWLEDGE BASE:
{kb_str}

GUIDELINES:
1. Be simple and clear - your users may be first-time voters.
2. Always be politically NEUTRAL. Never favour any party or candidate.
3. Use numbered steps when explaining a process.
4. End responses with: "Tip:  You might also want to know:" and suggest a follow-up question.
5. Keep answers under 250 words unless asked for more detail.
6. Support both Hindi and English questions.
7. CRITICAL: NEVER use the characters "Rs. ", "-" (en-dash), or "-" (em-dash). 
   - Instead of "Rs. ", always use "Rs.".
   - Instead of "-" or "-", always use a simple hyphen "-".
"""

@st.cache_resource
def get_gemini_model():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set.")
    return genai.Client(api_key=api_key)

def create_chat_session(client, kb_data, history=None):
    return client.chats.create(
        model="gemini-flash-lite-latest",
        config=types.GenerateContentConfig(
            system_instruction=get_system_prompt(kb_data),
            temperature=0.3,
            max_output_tokens=600,
        ),
        history=history
    )

def ask_votermitra(chat_session, user_message: str) -> str:
    try:
        response = chat_session.send_message(user_message)
        return response.text
    except Exception as e:
        return f"Warning:  Sorry, I ran into an issue: {str(e)}. Please try again."

def translate_messages(client, messages: list[dict], target_lang: str) -> None:
    import json
    texts = [m["content"] for m in messages]
    prompt = f"Translate the following JSON array of strings to {target_lang}. Preserve all formatting. Output ONLY a valid JSON array of strings:\n\n{json.dumps(texts)}"
    try:
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=prompt,
        )
        cleaned = response.text.strip()
        if cleaned.startswith("```json"): cleaned = cleaned[7:]
        if cleaned.endswith("```"): cleaned = cleaned[:-3]
        translated_texts = json.loads(cleaned.strip())
        
        if len(translated_texts) == len(messages):
            for i, msg in enumerate(messages):
                msg["content"] = translated_texts[i]
                if "audio" in msg: msg.pop("audio")
    except Exception as e:
        print(f"Batch Translation Error: {e}")

def extract_age_from_id(client, image_bytes: bytes) -> int:
    import datetime
    from google.genai import types
    
    prompt = "You are an OCR ID scanner. Extract the Date of Birth (DOB) from this ID card. If you find a DOB, calculate the current age based on today's date, and output ONLY the integer age. Do not output anything else. If you cannot find a DOB, output 20."
    try:
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                prompt
            ]
        )
        age_str = response.text.strip()
        return int(age_str)
    except Exception as e:
        print(f"OCR Error: {e}")
        return 20

def summarize_candidate(client, candidate: dict, target_lang: str) -> str:
    import json
    candidate_json = json.dumps(candidate, indent=2)
    prompt = f"""You are an unbiased, objective election analyst. Analyze the following candidate data extracted from their election affidavit.
Summarize the candidate's background into exactly 3 clear bullet points focusing on:
1. Educational background and profession.
2. Financial standing (Total Assets vs Liabilities).
3. Any red flags, specifically criminal cases.
Ensure the response is extremely concise and objective.
Translate the final output into {target_lang}.
CRITICAL: NEVER use the characters "Rs. ", "-" (en-dash), or "-" (em-dash). Use "Rs." and hyphens "-" instead.

Candidate Data:
{candidate_json}
"""
    try:
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        return f"Warning:  Could not generate summary. Error: {str(e)}"

def check_eligibility(age: int, is_citizen: bool, is_resident: bool, disqualified: bool, lang: str = "en") -> dict:
    from utils.translations import UI_TRANSLATIONS
    
    def t_local(key, **kwargs):
        text = UI_TRANSLATIONS.get(key, {}).get(lang, UI_TRANSLATIONS.get(key, {}).get("en", ""))
        return text.format(**kwargs)

    reasons = []
    next_steps = []
    eligible = True

    if age < 18:
        eligible = False
        reasons.append(f"(No) {t_local('err_age', age=age)}")
        next_steps.append(t_local('step_register_18'))
    else:
        reasons.append(f" {t_local('ok_age', age=age)}")

    if not is_citizen:
        eligible = False
        reasons.append(f"(No) {t_local('err_citizen')}")
    else:
        reasons.append(f" {t_local('ok_citizen')}")

    if not is_resident:
        eligible = False
        reasons.append(f"(No) {t_local('err_resident')}")
        next_steps.append(t_local('step_nri'))
    else:
        reasons.append(f"🏠 {t_local('ok_resident')}")

    if disqualified:
        eligible = False
        reasons.append(f"(No) {t_local('err_disqualified')}")

    if eligible:
        next_steps = [
            t_local('step_roll'),
            t_local('step_form6'),
            t_local('step_docs'),
            t_local('step_helpline'),
        ]

    return {
        "eligible": eligible,
        "reasons": reasons,
        "next_steps": next_steps
    }