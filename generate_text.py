import os
import json
import random
import re
from pathlib import Path

import google.generativeai as genai

# ---- CONFIG ----
MODEL_NAME = "models/gemini-2.5-flash"
DATA_DIR = Path("data")
USED_TEXTS_PATH = DATA_DIR / "used_texts.json"

EMOJIS = ["❤️", "💙", "🌸", "🌼", "🦚", "🕊️", "🙏", "✨", "🌿", "🌙", "🪔", "💫"]

EXAMPLE_LINES = [
    "जब सब छूट जाए, तब भी श्रीकृष्ण साथ रहते हैं। ❤️",
    "जिसने कृष्ण को पाया, उसने सब कुछ पा लिया। 🦚",
    "कृष्ण पर छोड़ दो, वह तुम्हें संभाल लेंगे। 🌿",
    "जहाँ भरोसा कृष्ण पर हो, वहाँ डर कभी टिकता नहीं। ✨",
    "कृष्ण का नाम ही हर समस्या का समाधान है। 🙏",
    "कृष्ण की शरण में गए तो फिर किसी सहारे की ज़रूरत नहीं। 🌼",
    "हर टूटे दिल की दवा सिर्फ़ एक — श्रीकृष्ण। 🕊️",
    "कृष्ण ने संभाल लिया, अब मुझे किसी बात का डर नहीं। 🌙",
    "कृष्ण चुप रहते हैं, लेकिन कभी गलत नहीं करते। 🔱",
]


# ---------- used_texts helpers ----------

def load_used_texts():
    if not USED_TEXTS_PATH.exists():
        return []
    try:
        with USED_TEXTS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x) for x in data]
        return []
    except Exception:
        return []


def save_used_texts(lines):
    USED_TEXTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with USED_TEXTS_PATH.open("w", encoding="utf-8") as f:
        json.dump(lines, f, ensure_ascii=False, indent=2)


def normalize_for_compare(text: str) -> str:
    text = re.sub(r"[^\w\s\u0900-\u097F]", "", text)  # keep Devanagari + letters/digits
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def is_too_similar(candidate: str, used_lines) -> bool:
    cand_norm = normalize_for_compare(candidate)
    if not cand_norm:
        return True

    for old in used_lines:
        old_norm = normalize_for_compare(old)
        if not old_norm:
            continue
        if cand_norm == old_norm:
            return True
        if cand_norm in old_norm or old_norm in cand_norm:
            return True
    return False


# ---------- Gemini interaction ----------

def clean_line(text: str) -> str:
    text = text.strip()
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
    emoji_str = "".join(EMOJIS)

    prompt = f"""
आप एक इंस्टाग्राम / यूट्यूब रील्स के लिए शॉर्ट टेक्स्ट लिखने वाले राइटर हैं।

काम:
- सिर्फ़ एक लाइन लिखिए।
- भाषा 100% HINDI (देवनागरी)। कोई English शब्द या अक्षर नहीं।
- फ़ोकस: भगवान कृष्ण / श्रीकृष्ण पर भरोसा, surrender, healing, gratitude, शांति।
- vibe deep हो लेकिन simple और relatable हो।
- लंबाई: लगभग 10–16 शब्द।
- लाइन के अंत में 1–3 प्यारे emoji इन में से लगाइए: {emoji_str}

स्टाइल के लिए कुछ example (इनको कॉपी नहीं करना, बस vibe समझना):

1. "जब सब छूट जाए, तब भी श्रीकृष्ण साथ रहते हैं।" ❤️
2. "जिसने कृष्ण को पाया, उसने सब कुछ पा लिया।" 🦚
3. "कृष्ण पर छोड़ दो, वह तुम्हें संभाल लेंगे।" 🌿
4. "जहाँ भरोसा कृष्ण पर हो, वहाँ डर कभी टिकता नहीं।" ✨
5. "कृष्ण का नाम ही हर समस्या का समाधान है।" 🙏
6. "हर टूटे दिल की दवा सिर्फ़ एक — श्रीकृष्ण।" 🕊️
7. "कृष्ण ने संभाल लिया, अब मुझे किसी बात का डर नहीं।" 🌙

कड़ाई से नियम:
- लाइन में कम से कम एक नाम ज़रूर हो:
  कृष्ण / श्रीकृष्ण / कान्हा / श्याम / गोपाल / माधव
- कोई hashtag नहीं (#), कोई quotes नहीं (" "), कोई English letter नहीं।
- सिर्फ़ वही एक लाइन लौटाइए, और कुछ नहीं।
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
    if not re.search(r"[\u0900-\u097F]", line):
        return False
    if re.search(r"[A-Za-z]", line):
        return False
    if not re.search(r"(कृष्ण|श्रीकृष्ण|कान्हा|श्याम|गोपाल|माधव)", line):
        return False
    if len(line.split()) < 4:
        return False
    return True


def get_krishna_line(max_attempts: int = 10) -> str:
    """Main function used by create_image.py"""
    used = load_used_texts()
    print(f"📚 Used lines so far: {len(used)}")

    try:
        model = configure_gemini()
    except Exception as e:
        print("⚠️ Gemini config error, fallback to examples:", e)
        line = random.choice(EXAMPLE_LINES)
        used.append(line)
        save_used_texts(used)
        return line

    last_valid = None

    for attempt in range(1, max_attempts + 1):
        print(f"👉 Attempt {attempt}/{max_attempts}...")
        try:
            candidate = generate_candidate_line(model)
        except Exception as e:
            print("⚠️ Gemini error:", e)
            continue

        if not is_valid_hindi_line(candidate):
            print("❌ Rejected: pure Hindi नहीं या कृष्ण नाम missing / बहुत छोटा।")
            continue

        if is_too_similar(candidate, used):
            print("🔁 Rejected: पुराने टेक्स्ट जैसा लग रहा है (duplicate vibe)।")
            continue

        used.append(candidate)
        save_used_texts(used)
        print("✅ Final chosen line:", candidate)
        return candidate

    # अगर ऊपर से कुछ नहीं मिला तो example से ले लो
    print("⚠️ Max attempts हो गए, example से लाइन ले रहे हैं।")
    fallback = random.choice(EXAMPLE_LINES)
    used.append(fallback)
    save_used_texts(used)
    return fallback


def main():
    line = get_krishna_line()
    print("\n✨ Krishna Hindi Line For Reel ✨")
    print(line)


if __name__ == "__main__":
    main()
