# generate_text.py
#
# Generates one short, deep Hindi Krishna line for reels.
# - Uses Gemini 2.5 Flash
# - Style: cute + devotional + emotional, with emojis (♥️🌸🦚 etc.)
# - No duplicates: remembers all past lines in state/used_lines.json
# - Can be imported as a function OR run as a script.
#
# When run directly: python generate_text.py
# It prints the line and saves it to output/krishna_line.txt

import os
import json
from pathlib import Path
from typing import List, Set

import google.generativeai as genai

# ---------- Paths & config ----------

ROOT_DIR = Path(__file__).resolve().parent
STATE_DIR = ROOT_DIR / "state"
OUTPUT_DIR = ROOT_DIR / "output"

STATE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

USED_LINES_PATH = STATE_DIR / "used_lines.json"
OUTPUT_LINE_PATH = OUTPUT_DIR / "krishna_line.txt"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "models/gemini-2.5-flash")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in environment.")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

# ---------- Helper functions ----------


def load_used_lines() -> Set[str]:
    if not USED_LINES_PATH.exists():
        return set()
    try:
        with USED_LINES_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data if isinstance(data, list) else [])
    except Exception:
        # If file is corrupted, start fresh (better than crashing the workflow)
        return set()


def save_used_lines(used: Set[str]) -> None:
    with USED_LINES_PATH.open("w", encoding="utf-8") as f:
        json.dump(sorted(used), f, ensure_ascii=False, indent=2)


def clean_text(text: str) -> str:
    # Basic trimming + collapse spaces
    line = " ".join(text.strip().split())
    # Remove leading bullets / numbers
    for prefix in ("-", "•", "*", "1.", "2.", "3.", "4.", "5."):
        if line.startswith(prefix + " "):
            line = line[len(prefix) + 1 :].strip()
    return line


def is_good_line(line: str, used: Set[str]) -> bool:
    if not line:
        return False

    # No duplicates
    if line in used:
        return False

    # Length constraints (you can tweak)
    if len(line) < 12 or len(line) > 80:
        return False

    # Must be in Hindi & Krishna-centric: check for common words
    hindi_chars = sum("\u0900" <= ch <= "\u097F" for ch in line)
    if hindi_chars < len(line) * 0.4:  # roughly at least 40% Devanagari
        return False

    if "कृष्ण" not in line and "श्रीकृष्ण" not in line and "कान्हा" not in line:
        return False

    return True


def call_gemini_for_candidates(used: Set[str]) -> List[str]:
    """Ask Gemini for multiple short lines in our exact style."""
    # We give it style examples + instructions
    prompt = """
तुम एक इंस्टाग्राम रील राइटर हो जो सिर्फ भगवान श्रीकृष्ण पर
गहरी, छोटी और दिल छू लेने वाली हिंदी पंक्तियाँ लिखता है।

रूल्स:
- सिर्फ हिंदी में लिखो।
- हर पंक्ति बहुत छोटी हो (लगभग 1 लाइन, 8–16 शब्द).
- टोन: भरोसा, surrender, कृतज्ञता, शांति, Krishna-भक्ति।
- प्यारे इमोजी यूज़ करो जैसे ♥️🌸🦚💫🕊️ (लेकिन ज़्यादा नहीं; 1–3 काफी हैं).
- हर पंक्ति अलग हो, दोहराव जैसा महसूस न हो।
- कोई लंबा paragraph या कविता नहीं, सिर्फ एक लाइन में बात खत्म करो।
- English words जितना हो सके avoid करो।

स्टाइल के उदाहरण (इनको दोहराना नहीं है, बस ऐसा feel रखना है):

1) "जब सब छूट जाए, तब भी श्रीकृष्ण साथ रहते हैं। ♥️"
2) "जिसने कृष्ण को पाया, उसने सब कुछ पा लिया। 🌸"
3) "कृष्ण पर छोड़ दो, वह तुम्हें संभाल लेंगे। 🕊️"
4) "जहाँ भरोसा कृष्ण पर हो, वहाँ डर टिक ही नहीं पाता। 💫"
5) "कृष्ण का नाम ही हर चिंता की आख़िरी दवा है। 🦚"
6) "कृष्ण की शरण में आया दिल कभी खाली नहीं लौटता। ♥️"
7) "जो कुछ भी है, बस कृष्ण की कृपा से है। 🌸"
8) "कृष्ण संभाल रहे हैं, इसलिए मैं बेफ़िक्र हूँ। 💙"
9) "कान्हा की चुप्पी भी हमारे हक़ में फैसला होती है। 🕊️"
10) "जिसे कृष्ण मिला, उसे किसी और सहारे की ज़रूरत नहीं। 🦚"

अब ऊपर दिए गए example दोहराए बिना,
5 नई और यूनिक पंक्तियाँ लिखो।
हर पंक्ति नई लाइन पर लिखो।
"""

    print("🕉️ Asking Gemini for fresh Krishna lines...")
    resp = model.generate_content(prompt)
    # Newer SDK exposes `.text`
    raw = getattr(resp, "text", None)
    if not raw:
        # Fallback: join candidate parts if needed
        parts = []
        for cand in getattr(resp, "candidates", []) or []:
            for p in getattr(cand, "content", {}).parts or []:
                if getattr(p, "text", None):
                    parts.append(p.text)
        raw = "\n".join(parts)

    if not raw:
        raise RuntimeError("Gemini did not return any text.")

    lines = [clean_text(l) for l in raw.splitlines() if l.strip()]
    print("📝 Gemini raw lines:")
    for l in lines:
        print("   -", l)

    return lines


def generate_unique_krishna_line(max_attempts: int = 6) -> str:
    used = load_used_lines()

    for attempt in range(1, max_attempts + 1):
        print(f"👉 Gemini attempt {attempt}...")
        candidates = call_gemini_for_candidates(used)

        for line in candidates:
            if is_good_line(line, used):
                print("✅ Chosen line:", line)
                used.add(line)
                save_used_lines(used)
                return line

        print("⚠️ No good unique line found in this attempt, retrying...")

    raise RuntimeError("Could not generate a new unique Krishna line after several attempts.")


# ---------- CLI ----------

if __name__ == "__main__":
    line = generate_unique_krishna_line()
    print("\n🌸 Final Krishna line for today:")
    print(line)

    # Save for other scripts (image/video builder)
    with OUTPUT_LINE_PATH.open("w", encoding="utf-8") as f:
        f.write(line)

    print(f"\n💾 Saved to: {OUTPUT_LINE_PATH}")
