import os
import json
import random
from typing import List

import google.generativeai as genai

# -----------------------------
# Config
# -----------------------------

USED_TEXTS_FILE = "data/used_texts.json"

# Safe-ish fallback Hindi lines (Krishna themed, deep + short)
FALLBACK_LINES: List[str] = [
    "जब सब रास्ते बंद हो जाएँ, तब श्रीकृष्ण का रास्ता खुल जाता है। ✿",
    "मन की हर उलझन सुलझ जाती है, जब विश्वास श्रीकृष्ण पर हो। ♡",
    "जिसे कृष्ण संभाल रहे हों, उसे दुनिया की चिंता करने की ज़रूरत नहीं। ❀",
    "कृष्ण पर छोड़ दो, वो वहाँ रास्ता बनाएँगे जहाँ कोई रास्ता दिखता भी नहीं। ♥",
    "कृष्ण का नाम लेने वाला कभी अकेला नहीं चलता। ✿",
    "जितना भरोसा कृष्ण पर बढ़ाते जाओगे, उतना डर अपने आप घटता जाएगा। ♡",
    "कृष्ण की मर्जी पर राज़ी हो जाओ, दिल अपने आप हल्का हो जाएगा। ❀",
    "हर टूटे दिल की मरहम — बस एक नाम, श्रीकृष्ण। ♥",
    "कृष्ण चुप रहते हैं, लेकिन कभी गलत नहीं करते। ✿",
    "जो हो रहा है, वही तुम्हारे लिए सही है — ये भरोसा कृष्ण देते हैं। ♡",
]

# Gemini model name (from your successful test_gemini run)
GEMINI_MODEL_NAME = "models/gemini-2.5-flash"


# -----------------------------
# Utils for storing used texts
# -----------------------------

def load_used_texts() -> List[str]:
    os.makedirs(os.path.dirname(USED_TEXTS_FILE), exist_ok=True)
    if not os.path.exists(USED_TEXTS_FILE):
        with open(USED_TEXTS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return []
    try:
        with open(USED_TEXTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # If file corrupted, reset
        return []


def save_used_texts(texts: List[str]) -> None:
    os.makedirs(os.path.dirname(USED_TEXTS_FILE), exist_ok=True)
    with open(USED_TEXTS_FILE, "w", encoding="utf-8") as f:
        json.dump(texts, f, ensure_ascii=False, indent=2)


# -----------------------------
# Gemini helpers
# -----------------------------

def setup_gemini() -> genai.GenerativeModel:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(GEMINI_MODEL_NAME)


def call_gemini_for_line() -> str:
    """
    Ask Gemini for one short, deep Krishna-themed Hindi line.
    We explicitly ask NOT to use emoji characters, only simple cute symbols.
    """
    model = setup_gemini()

    prompt = """
तुम्हारा काम है एक बहुत छोटा, बहुत गहरा और पॉज़िटिव कृष्ण-कोट देना।
शर्तें:
- भाषा: केवल शुद्ध और आसान हिन्दी।
- विषय: भरोसा, surrender, शांति, कृष्ण का सहारा, डर का खत्म होना।
- लम्बाई: ज़्यादा से ज़्यादा 1–2 छोटी लाइनें (10–18 शब्द)।
- स्टाइल: इंस्टाग्राम रील टेक्स्ट जैसा, बहुत relatable और दिल को छू लेने वाला।
- इमोजी: ❌ कोई भी emoji मत use करो (जैसे ❤️ 🙂 🌸)।
- केवल ये symbols use कर सकते हो: ♥ ♡ ✿ ❀ ❁ ✧ ✨
- आउटपुट: सिर्फ़ लाइन लिखो, कोई extra explanation या quotes (“ ”) मत लगाओ।

उदाहरण स्टाइल (बस अंदाज़ समझने के लिए):
- "जब सब छूट जाए, तब भी श्रीकृष्ण साथ रहते हैं। ♡"
- "जहाँ भरोसा कृष्ण पर हो, वहाँ डर टिक ही नहीं सकता। ✿"
- "कृष्ण पर छोड़ दो, वो तुम्हें कभी गिरने नहीं देंगे। ♥"
"""

    resp = model.generate_content(prompt)

    # For google-generativeai >= 0.8, text is in .text
    text = getattr(resp, "text", None)
    if not text:
        # Some versions return candidates; handle that too
        try:
            if resp.candidates and resp.candidates[0].content.parts:
                maybe = resp.candidates[0].content.parts[0].text
                text = maybe
        except Exception:
            pass

    if not text:
        raise RuntimeError("Gemini did not return text.")

    return clean_text(text)


# -----------------------------
# Cleaning & uniqueness
# -----------------------------

def clean_text(raw: str) -> str:
    """Normalize whitespace and strip quotes / spaces."""
    line = raw.strip()
    # Remove surrounding quotes if present
    if (line.startswith('"') and line.endswith('"')) or (line.startswith("“") and line.endswith("”")):
        line = line[1:-1].strip()

    # Gemini sometimes adds bullet or dash at start
    if line.startswith("- "):
        line = line[2:].strip()

    # Collapse multiple spaces/newlines
    line = " ".join(line.split())
    return line


def generate_unique_krishna_line(max_attempts: int = 6) -> str:
    used = load_used_texts()

    # First try Gemini a few times
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"👉 Gemini attempt {attempt}...")
            candidate = call_gemini_for_line()
            print(f"   Candidate: {candidate}")
            if candidate and candidate not in used:
                used.append(candidate)
                save_used_texts(used)
                return candidate
        except Exception as e:
            print(f"   Gemini error on attempt {attempt}: {e}")
            last_error = e

    print("⚠️ Falling back to local Hindi lines...")
    # Fallback: pick from hardcoded list, also avoiding duplicates
    random.shuffle(FALLBACK_LINES)
    for line in FALLBACK_LINES:
        cleaned = clean_text(line)
        if cleaned not in used:
            used.append(cleaned)
            save_used_texts(used)
            return cleaned

    # Absolute last resort
    if FALLBACK_LINES:
        return clean_text(FALLBACK_LINES[0])

    raise RuntimeError(f"Unable to generate line, last Gemini error: {last_error}")


# -----------------------------
# PUBLIC API for other scripts
# -----------------------------

def get_krishna_line() -> str:
    """
    This is the function used by create_image.py.
    It returns one unique, deep Hindi Krishna line.
    """
    return generate_unique_krishna_line()


# -----------------------------
# CLI usage (manual test)
# -----------------------------

if __name__ == "__main__":
    line = get_krishna_line()
    print("Generated Krishna line:")
    print(line)
