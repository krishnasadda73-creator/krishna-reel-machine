import os
import json
import random
import re
from pathlib import Path

import google.generativeai as genai

# Use a good Gemini model name that exists in your project
MODEL_NAME = "models/gemini-2.5-flash"

DATA_DIR = Path("data")
USED_TEXTS_PATH = DATA_DIR / "used_texts.json"


# ---------- Helpers for used-text history ----------

def load_used_texts():
    """Load the list of already-used lines from JSON."""
    if not USED_TEXTS_PATH.exists():
        return []

    try:
        with USED_TEXTS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x) for x in data]
        return []
    except Exception:
        # If file is corrupted, start fresh
        return []


def save_used_texts(lines):
    """Save list of used lines to JSON."""
    USED_TEXTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with USED_TEXTS_PATH.open("w", encoding="utf-8") as f:
        json.dump(lines, f, ensure_ascii=False, indent=2)


def normalize_for_compare(text: str) -> str:
    """Normalize line for similarity comparison."""
    # Remove emojis and punctuation, lower, collapse spaces
    text = re.sub(r"[^\w\s\u0900-\u097F]", "", text)  # keep letters + Devanagari + digits + underscore
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def is_too_similar(candidate: str, used_lines) -> bool:
    """Check if candidate is basically the same as any used line."""
    cand_norm = normalize_for_compare(candidate)
    if not cand_norm:
        return True

    for old in used_lines:
        old_norm = normalize_for_compare(old)
        if not old_norm:
            continue

        # Exact match
        if cand_norm == old_norm:
            return True

        # One contained in the other (very similar)
        if cand_norm in old_norm or old_norm in cand_norm:
            return True

    return False


# ---------- Gemini interaction ----------

EMOJIS = ["❤️", "💙", "🌸", "🌼", "🦚", "🕊️", "🙏", "✨", "🌿", "🌙", "🪔", "💫"]

EXAMPLE_LINES = [
    "जब सब छूट जाए, तब भी श्रीकृष्ण साथ रहते हैं। ❤️",
    "जिसने कृष्ण को पाया, उसने सब कुछ पा लिया। 🦚",
    "कृष्ण पर छोड़ दो, वह तुम्हें संभाल लेंगे। 🌿",
    "जहाँ भरोसा कृष्ण पर हो, वहाँ डर कभी टिकता नहीं। ✨",
    "कृष्ण का नाम ही हर समस्या का समाधान है। 🙏",
    "कृष्ण की शरण में गए तो फिर किसी सहारे की ज़रूरत नहीं। 🌼",
    "हर टूटे दिल की दवा सिर्फ एक — श्रीकृष्ण। 🕊️",
    "कृष्ण ने संभाल लिया, अब मुझे किसी बात का डर नहीं। 🌙",
    "कृष्ण चुप रहते हैं, लेकिन कभी गलत नहीं करते। 🔱",
]


def clean_line(text: str) -> str:
    """Basic cleanup: remove quotes & extra spaces."""
    text = text.strip()
    # Remove surrounding quotes
    text = re.sub(r'^[\"“”\'‘’]+', "", text)
    text = re.sub(r'[\"“”\'‘’]+$', "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def configure_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(MODEL_NAME)


def generate_candidate_line(model) -> str:
    """Ask Gemini for ONE Hindi Krishna line."""
    emoji_str = "".join(EMOJIS)

    prompt = f"""
आप एक शॉर्ट इंस्टाग्राम/रील्स टेक्स्ट राइटर हैं।

एक ही लाइन में गहरा, पॉज़िटिव और भक्तिमय टेक्स्ट लिखिए, जो भगवान कृष्ण / श्रीकृष्ण पर केंद्रित हो।

⚠️ बहुत ज़रूरी नियम:
- भाषा: सिर्फ़ HINDI (देवनागरी), कोई भी English शब्द नहीं।
- टोन: दिल को शांत करने वाला, भरोसा, surrender, faith, healing, gratitude।
- लंबाई: ज़्यादा से ज़्यादा 14–16 शब्द।
- स्टाइल: नीचे दिए गए उदाहरणों जैसा vibe, लेकिन कॉपी नहीं करना:

1. "जब सब छूट जाए, तब भी श्रीकृष्ण साथ रहते हैं।" ❤️
2. "जिसने कृष्ण को पाया, उसने सब कुछ पा लिया।" 🦚
3. "कृष्ण पर छोड़ दो, वह तुम्हें संभाल लेंगे।" 🌿
4. "जहाँ भरोसा कृष्ण पर हो, वहाँ डर कभी टिकता नहीं।" ✨
5. "कृष्ण का नाम ही हर समस्या का समाधान है।" 🙏
6. "कृष्ण की शरण में गए तो फिर किसी सहारे की ज़रूरत नहीं।" 🌼
7. "हर टूटे दिल की दवा सिर्फ एक — श्रीकृष्ण।" 🕊️
8. "कृष्ण ने संभाल लिया, अब मुझे किसी बात का डर नहीं।" 🌙
9. "कृष्ण चुप रहते हैं, लेकिन कभी गलत नहीं करते।" 🔱

और नियम:
- लाइन में कम से कम एक नाम ज़रूर हो: कृष्ण / श्रीकृष्ण / कान्हा / माधव / गोपाल / श्याम।
- लाइन के END में 1 से 3 प्यारे emoji लगाइए (इनमें से चुनें: {emoji_str}).
- कोई hashtag नहीं (#), कोई quotes नहीं (" "), कोई English अक्षर नहीं।
- सिर्फ़ एक ही लाइन लौटाइए, और कुछ नहीं।
"""

    print("🕉️ Gemini से हिंदी कृष्ण लाइन माँग रहे हैं...")
    response = model.generate_content(prompt)
    text = getattr(response, "text", "").strip()
    if not text:
        raise RuntimeError("Gemini से खाली response मिला।")
    line = clean_line(text)
    print(f"📜 Candidate: {line}")
    return line


def is_valid_hindi_line(line: str) -> bool:
    """Ensure line is Hindi-only and mentions Krishna."""
    # Must contain some Devanagari chars
    if not re.search(r"[\u0900-\u097F]", line):
        return False
    # No English letters allowed
    if re.search(r"[A-Za-z]", line):
        return False
    # Must mention some Krishna name
    if not re.search(r"(कृष्ण|श्रीकृष्ण|कान्हा|श्याम|गोपाल|माधव)", line):
        return False
    # Reasonable length check
    if len(line.split()) < 4:
        return False
    return True


def generate_unique_krishna_line(max_attempts: int = 10) -> str:
    """Generate a Hindi Krishna line, making sure it's not a duplicate."""
    model = configure_gemini()
    used = load_used_texts()
    print(f"📚 Used lines so far: {len(used)}")

    last_good = None

    for attempt in range(1, max_attempts + 1):
        print(f"👉 Attempt {attempt}/{max_attempts}...")
        try:
            candidate = generate_candidate_line(model)
        except Exception as e:
            print("⚠️ Gemini error:", e)
            continue

        if not is_valid_hindi_line(candidate):
            print("❌ Rejected: लाइन pure हिंदी नहीं या कृष्ण का नाम नहीं।")
            continue

        if is_too_similar(candidate, used):
            print("🔁 Rejected: यह लाइन पहले जैसी ही है (duplicate vibe)।")
            continue

        # Accept this one
        used.append(candidate)
        save_used_texts(used)
        print("✅ Final chosen line:", candidate)
        return candidate

    # अगर max_attempts के बाद भी कुछ नहीं मिला, तो आख़िरी candidate ही दे दो
    if last_good:
        print("⚠️ Max attempts हो गए, आख़िरी valid लाइन ले रहे हैं:", last_good)
        return last_good

    raise RuntimeError("कोई भी valid हिंदी कृष्ण लाइन नहीं बन पाई।")


def main():
    line = generate_unique_krishna_line()
    # सिर्फ़ प्रिंट करेंगे — create_image.py इसको import करके यूज़ करेगा
    print("\n✨ Krishna Hindi Line For Reel ✨")
    print(line)


if __name__ == "__main__":
    main()
