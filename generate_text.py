import os
import json
import time
import random
from pathlib import Path

import google.generativeai as genai

# --------------------------------------------------
# Config
# --------------------------------------------------
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

USED_TEXTS_FILE = DATA_DIR / "used_texts.json"

GEMINI_MODEL_NAME = "models/gemini-2.5-flash"
MAX_RETRIES = 6

# Symbols that are usually supported in normal fonts (NOT color emojis)
# These give a cute bhakti vibe without turning into squares.
CUTE_SYMBOLS = ["♥", "♡", "❣", "✿", "★", "☆", "✧"]


# --------------------------------------------------
# Helpers for used-text tracking
# --------------------------------------------------
def load_used_texts():
    if USED_TEXTS_FILE.exists():
        try:
            with open(USED_TEXTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def save_used_texts(texts):
    try:
        with open(USED_TEXTS_FILE, "w", encoding="utf-8") as f:
            json.dump(texts, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def strip_to_hindi_and_symbols(text: str) -> str:
    """
    Keep only:
      - Devanagari characters
      - basic punctuation
      - our allowed cute symbols
    This prevents weird squares in the video.
    """
    allowed_extra = set(CUTE_SYMBOLS)
    cleaned_chars = []
    for ch in text:
        code = ord(ch)
        if 0x0900 <= code <= 0x097F:  # Devanagari block
            cleaned_chars.append(ch)
        elif ch in " .,!?:;—-…'\"।॥":
            cleaned_chars.append(ch)
        elif ch in allowed_extra:
            cleaned_chars.append(ch)
    return "".join(cleaned_chars).strip()


# --------------------------------------------------
# Gemini setup
# --------------------------------------------------
def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY env var not set")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(GEMINI_MODEL_NAME)


# Base prompt: pure Hindi, no emojis, one deep line
BASE_PROMPT = """
आप एक रील के लिए छोटी, गहरी और दिल छू लेने वाली कृष्ण भक्तिमय पंक्ति लिख रहे हैं।

कड़ाई से नियम:
- भाषा: केवल हिन्दी, देवनागरी लिपि में।
- 1 ही पंक्ति लिखें।
- शब्द सीमा: लगभग 8–18 शब्द।
- लाइन बहुत गहरी, पॉज़िटिव और कृष्ण-केंद्रित हो:
  • भरोसा, समर्पण, सुरक्षा, धैर्य, प्रतीक्षा, टूटने के बाद संभलना, उम्मीद, शरण, प्रेम।
- टोन कुछ ऐसा हो (इनको कॉपी मत करना, सिर्फ भावना समझें):
  1) "जब सब छूट जाए, तब भी श्रीकृष्ण साथ रहते हैं।"
  2) "कृष्ण पर छोड़ दो, वह तुम्हें संभाल लेंगे।"
  3) "जहाँ भरोसा कृष्ण पर हो, वहाँ डर कभी टिकता नहीं।"
  4) "हर टूटे दिल की दवा सिर्फ एक — श्रीकृष्ण।"
  5) "कृष्ण की शरण में गए तो फिर किसी सहारे की ज़रूरत नहीं।"

सख्त मना:
- कोई इमोजी नहीं।
- अंग्रेज़ी शब्द, हैशटैग, नंबर, उद्धरणचिह्न आदि नहीं।
- "कैप्शन", "रील", "वीडियो", "इंस्टाग्राम" जैसे शब्द नहीं।

केवल एक तैयार पंक्ति देवनागरी में लौटाएँ, उसके आगे-पीछे कुछ भी अतिरिक्त न लिखें।
"""


def ask_gemini_for_line(model) -> str | None:
    try:
        resp = model.generate_content(BASE_PROMPT)
    except Exception as e:
        print(f"❌ Gemini error while generating text: {e}")
        return None

    # Normal way for new SDK
    raw = getattr(resp, "text", None)
    if not raw:
        # Fallback to older style
        try:
            raw = resp.candidates[0].content.parts[0].text
        except Exception:
            raw = None

    if not raw:
        return None

    raw = raw.strip().replace("\n", " ")
    raw = normalize_text(raw)

    # Only keep Hindi + allowed symbols
    cleaned = strip_to_hindi_and_symbols(raw)
    cleaned = normalize_text(cleaned)

    if not cleaned:
        return None

    return cleaned


def add_cute_symbols(line: str) -> str:
    """
    Randomly add 0–2 cute symbols at the end,
    separated by a space, e.g.
    '... कृष्ण पर भरोसा हो।  ♥✿'
    """
    # 50% chance to add symbols
    if random.random() < 0.4:
        return line

    count = random.choice([1, 2])
    chosen = random.sample(CUTE_SYMBOLS, k=count)
    suffix = "".join(chosen)
    # two spaces so text is slightly separated from sentence end
    return f"{line}  {suffix}"


# --------------------------------------------------
# Main public function
# --------------------------------------------------
def generate_unique_krishna_line() -> str:
    used_texts = load_used_texts()
    used_set = {normalize_text(t) for t in used_texts}

    model = get_gemini_client()

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"👉 Gemini attempt {attempt}...")
        base_line = ask_gemini_for_line(model)

        if not base_line:
            print("   Got empty/invalid line, retrying...")
            time.sleep(1.5)
            continue

        # Add cute symbols after Gemini to avoid confusing the model
        line = add_cute_symbols(base_line)
        norm = normalize_text(line)

        if norm in used_set:
            print("   Duplicate line detected, trying again...")
            time.sleep(1.0 + random.random())
            continue

        print(f"   ✅ Final Krishna line: {line}")
        used_texts.append(line)

        if len(used_texts) > 1000:
            used_texts = used_texts[-800:]

        save_used_texts(used_texts)
        return line

    fallback = "जब सब छूट जाए, तब भी श्रीकृष्ण साथ रहते हैं।  ♥"
    print(f"⚠️ Using fallback line after {MAX_RETRIES} failed attempts: {fallback}")
    return fallback


if __name__ == "__main__":
    print(generate_unique_krishna_line())
