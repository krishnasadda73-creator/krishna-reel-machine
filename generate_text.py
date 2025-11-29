# generate_text.py
import os
import time
from typing import List

import google.generativeai as genai

# ---------- CONFIG ----------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = "models/gemini-2.0-flash"  # from your working list
USED_LINES_FILE = "used_lines.txt"

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in environment.")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(MODEL_NAME)


# ---------- UTILS ----------

def ensure_used_file_exists() -> None:
    """Make sure used_lines.txt exists."""
    if not os.path.exists(USED_LINES_FILE):
        with open(USED_LINES_FILE, "w", encoding="utf-8") as f:
            f.write("")


def load_used_lines() -> List[str]:
    ensure_used_file_exists()
    with open(USED_LINES_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines() if line.strip()]


def save_used_line(line: str) -> None:
    ensure_used_file_exists()
    with open(USED_LINES_FILE, "a", encoding="utf-8") as f:
        f.write(line.strip() + "\n")


def clean_line(text: str) -> str:
    """Clean up response – single line, trimmed, no quotes."""
    if not text:
        return ""

    text = text.strip()

    # remove surrounding quotes if any
    if (text.startswith("“") and text.endswith("”")) or \
       (text.startswith('"') and text.endswith('"')) or \
       (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()

    # remove extra newlines (Gemini sometimes adds them)
    text = " ".join(text.splitlines())
    text = " ".join(text.split())  # collapse multiple spaces

    # hard length cap so it fits nicely on 2–3 lines
    if len(text) > 120:
        text = text[:120].rstrip(" ,।…") + "…"

    return text


def is_valid_line(text: str) -> bool:
    """Basic sanity checks."""
    if not text:
        return False
    if len(text) < 6:      # too tiny
        return False
    if "Write" in text or "यहाँ" in text or "यहां" in text:
        # sometimes model returns meta-instructions
        return False
    return True


# ---------- GEMINI CALL ----------

PROMPT = """
एक छोटी, गहरी, दिल को छू लेने वाली हिन्दी पंक्ति लिखो
जो श्रीकृष्ण पर भरोसा, समर्पण, कृतज्ञता और आशा के बारे में हो।

शर्तें:
- सिर्फ एक ही पंक्ति (कोई बुलेट पॉइंट या लिस्ट नहीं)
- 8–18 शब्दों के बीच
- सिर्फ हिन्दी (केवल इमोजी allowed)
- कोई हैशटैग नहीं, कोई उद्धरण चिन्ह (" ") नहीं
- इंस्टाग्राम रील के लिए relatable, simple, लेकिन बहुत गहरी लाइन

उदाहरण टोन (सिर्फ टोन के लिए, कॉपी मत करो):
- "जितना छोड़ोगे, उतना कृष्ण थाम लेंगे। 🦚"
- "कृष्ण साथ हों तो देर लग सकती है, पर चूक कभी नहीं। ❤️"

अब अपनी एक नई, यूनिक पंक्ति दो।
"""


def generate_from_gemini() -> str:
    """Ask Gemini once and return a cleaned Hindi line (may be empty)."""
    response = model.generate_content(PROMPT)
    # In v1, helper .text gives combined text output
    raw = getattr(response, "text", None)
    return clean_line(raw)


def get_final_line(max_attempts: int = 6) -> str:
    """
    Get a unique, valid Hindi Krishna line.
    - Tries Gemini a few times
    - Avoids duplicates using used_lines.txt
    - Falls back to safe default if needed
    """
    used = set(load_used_lines())

    last_good = None

    for attempt in range(1, max_attempts + 1):
        try:
            print(f"👉 Gemini attempt {attempt}...")
            line = generate_from_gemini()
            print(f"   Candidate: {line!r}")

            if not is_valid_line(line):
                continue

            if line in used:
                print("   Skipping – already used before.")
                continue

            last_good = line
            break

        except Exception as e:
            print(f"   ⚠️ Error in attempt {attempt}: {e}")
            time.sleep(1.0)

    if not last_good:
        # ultimate fallback – still deep and Krishna-centric
        last_good = "कृष्ण पर छोड़ दो, वो वहीं से संभाल लेंगे जहाँ तुम टूट जाते हो। 🦚"

    save_used_line(last_good)
    return last_good


if __name__ == "__main__":
    line = get_final_line()
    print("FINAL_LINE::", line)
