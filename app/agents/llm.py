"""LLM client — Groq (default) or OpenAI-compatible."""
import json
import os
import re
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# Default: Groq
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def call_llm(system: str, user: str, temperature: float = 0.1) -> str:
    """Return model text. Falls back to heuristic marker if no key works."""
    if LLM_PROVIDER == "groq" and GROQ_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1",
            )
            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"[LLM_ERROR] {e}"

    if LLM_PROVIDER == "openai" and OPENAI_API_KEY and OPENAI_API_KEY != "your_openai_api_key_here":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"[LLM_ERROR] {e}"

    return "[NO_LLM]"


def extract_json(text: str) -> Optional[dict]:
    """Best-effort JSON extraction from model output."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return None
    return None
