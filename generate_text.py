import os
import json
from pathlib import Path

from google import genai

# -------- CONFIG --------
MODEL_NAME = "gemini-2.0-flash"  # from your working model list
DATA_DIR = Path("data")
USED_TEXTS_FILE = DATA_DIR / "used_texts.json"


def load_used_texts():
    """Load previously used lines so we never repeat."""
    if not USED_TEXTS_FILE.exists():
        return []

    try:
        with open(USED_TEXTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        # If file is corrupted, just reset it
        return []


def save_used_texts(lines):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(USED_TEXTS_FILE, "w", encoding="utf-8") as f:
        json.dump(lines, f, ensure_ascii=False, indent=2)


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")
    return genai.Client(api_key=api_key)


def build_prompt():
    """
    Prompt for one deep, Krishna-focused line.
    Style should match the screenshots:
      - short, calm, devotional
      - about trust, surrender, protection, guidance
    """
    return (
        "Write ONE short, deep devotional quote about Lord Krishna in English.\n"
        "- Focus on trust, surrender, gratitude or protection by Krishna.\n"
        "- Max 14 words.\n"
        "- No hashtags.\n"
        "- No quotation marks around the line.\n"
        "- Feel like Instagram reel text: simple but powerful.\n"
        "Example style (DO NOT copy, just feel):\n"
        "  He knows and that's enough.\n"
        "  Accept it and leave it to Him. He knows better than you.\n"
        "Now write ONE new line."
    )


def clean_text(text: str) -> str:
    """Make the line single-line, remove quotes etc."""
    if not text:
        return ""
    text = text.strip()
    # Remove newlines
    text = " ".join(text.split())
    # Remove leading/trailing quotes
    for ch in ['"', "“", "”", "'"]:
        if text.startswith(ch) and text.endswith(ch):
            text = text[1:-1].strip()
    return text


def extract_text_from_response(response) -> str:
    """
    Handle google-genai response formats.
    Preferred: response.text
    Fallback: first candidate/part text.
    """
    # New client has .text
    if hasattr(response, "text") and isinstance(response.text, str):
        return response.text

    # Fallback – dig into candidates
    try:
        cands = getattr(response, "candidates", None) or []
        for c in cands:
            content = getattr(c, "content", None)
            if not content:
                continue
            parts = getattr(content, "parts", None) or []
            for p in parts:
                t = getattr(p, "text", None)
                if isinstance(t, str) and t.strip():
                    return t
    except Exception:
        pass

    return ""


def generate_unique_krishna_line(max_retries: int = 6) -> str:
    client = get_gemini_client()
    used_lines = load_used_texts()

    prompt = build_prompt()

    for attempt in range(1, max_retries + 1):
        print(f"👉 Gemini attempt {attempt}...")

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
        )

        raw_text = extract_text_from_response(response)
        line = clean_text(raw_text)

        print(f"   Candidate: {line}")

        if not line:
            print("   Empty/invalid text, retrying...")
