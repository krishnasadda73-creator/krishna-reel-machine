import os
import json
import random
from pathlib import Path
from difflib import SequenceMatcher

from google import genai

# ---------- Config ----------

STATE_DIR = Path("state")
STATE_DIR.mkdir(parents=True, exist_ok=True)

USED_LINES_FILE = STATE_DIR / "used_lines.json"

# Use the good model we already tested
GEMINI_MODEL = "models/gemini-2.5-flash"


# ---------- State helpers ----------

def load_used_lines():
    if not USED_LINES_FILE.exists():
        return []
    try:
        with open(USED_LINES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def save_used_lines(lines):
    with open(USED_LINES_FILE, "w", encoding="utf-8") as f:
        json.dump(lines, f, ensure_ascii=False, indent=2)


# ---------- Text helpers ----------

def clean_text(text: str) -> str:
    if not text:
        return ""

    t = text.strip()

    # Remove outer quotes
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        t = t[1:-1].strip()

    # Replace multiple spaces
    while "  " in t:
        t = t.replace("  ", " ")

    # Capitalise first letter
    if t and not t[0].isupper():
        t = t[0].upper() + t[1:]

    # Hard length limit
    words = t.split()
    if len(words) > 18:
        t = " ".join(words[:18])

    return t


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# ---------- Gemini call ----------

def call_gemini_once() -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in environment.")

    client = genai.Client(api_key=api_key)

    prompt = """
You are writing a ONE-LINE devotional caption about Lord Krishna.

Rules:
- Language: English only, but with Indian devotional vibe.
- Theme: surrender, trust, gratitude, protection, Krishna's presence.
- Length: 5–16 words.
- Tone: deep, peaceful, comforting, like the sample reels Uday likes.
- No hashtags, no quotes around the line.
- At most ONE emoji at the end (optional, like ❤️ or 🙏).
- Output ONLY the caption line, nothing else.
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    # New google-genai responses expose .text
    text = getattr(response, "text", None)
    return (text or "").strip()


# ---------- Main caption generator ----------

def generate_unique_krishna_line(max_attempts: int = 6) -> str:
    used_lines = load_used_lines()
    print(f"🧾 Already have {len(used_lines)} used captions")

    # how strict we are on "duplicate"
    threshold = 0.78

    best_candidate = None
    best_distance = -1.0  # 1 - max_similarity

    for attempt in range(1, max_attempts + 1):
        print(f"👉 Gemini attempt {attempt}...")
        try:
            raw = call_gemini_once()
        except Exception as e:
            print(f"   ⚠️ Gemini error: {e!r}")
            continue

        line = clean_text(raw)
        if not line:
            print("   ⚠️ Empty/invalid line, skipping.")
            continue

        if not used_lines:
            # first ever line, just use it
            used_lines.append(line)
            save_used_lines(used_lines)
            print(f"✅ Using first line: {line}")
            return line

        # compute similarity vs ALL used lines
        sims = [similarity(line, u) for u in used_lines]
        max_sim = max(sims) if sims else 0.0

        print(f"   Candidate: {line}")
        print(f"   Max similarity vs history: {max_sim:.3f}")

        if max_sim < threshold:
            # distinct enough → accept
            used_lines.append(line)
            save_used_lines(used_lines)
            print(f"🎉 Accepted fresh line: {line}")
            return line

        # too similar, keep track of "least bad" option as fallback
        distance = 1.0 - max_sim
        if distance > best_distance:
            best_distance = distance
            best_candidate = line

        print("   ↩️ Rejected as too similar, trying again...")

    # If we get here: all attempts were "similar"
    if best_candidate:
        used_lines.append(best_candidate)
        save_used_lines(used_lines)
        print("⚠️ All attempts were similar; using the best fallback:")
        print(f"   {best_candidate}")
        return best_candidate

    # Final safety fallback
    fallback = "In Krishna's embrace, your heart is always safe."
    used_lines.append(fallback)
    save_used_lines(used_lines)
    print("⚠️ Gemini failed completely; using static fallback line.")
    return fallback


if __name__ == "__main__":
    line = generate_unique_krishna_line()
    print("\nFinal caption:", line)
