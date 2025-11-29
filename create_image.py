# create_image.py
#
# 1) Pick a random Krishna image from images/
# 2) Ask Gemini to write a deep Hindi Krishna line (with cute emojis)
# 3) Make sure the line is:
#       - Hindi-only
#       - Short, deep, positive
#       - Focused on Krishna
#       - NOT a duplicate of previous lines
# 4) Draw the text on a 1080x1920 canvas with the image
# 5) Save PNG into output/ for the video step

import os
import json
import random
from typing import List, Set

from PIL import Image, ImageDraw, ImageFont

import google.generativeai as genai

# ---------------- CONFIG ---------------- #

MODEL_NAME = "models/gemini-flash-latest"
IMAGES_DIR = "images"
OUTPUT_DIR = "output"
STATE_DIR = "state"
STATE_FILE = os.path.join(STATE_DIR, "used_lines.json")

# We'll save the same frame under a few common names so create_video.py
# can always find at least one PNG.
OUTPUT_FRAME_NAMES = [
    "krishna_frame.png",
    "frame.png",
    "reel_frame.png",
]

# Cute emojis we allow / sometimes append
EMOJIS = ["❤️", "🌸", "🦚", "🕊️", "✨", "💙", "🌿", "🌙"]

# These are example styles (user’s vibe) – we also treat them as "already used"
STYLE_EXAMPLES = [
    "जब सब छूट जाए, तब भी श्रीकृष्ण साथ रहते हैं। ❤️",
    "जिसने कृष्ण को पाया, उसने सब कुछ पा लिया। 🌸",
    "कृष्ण पर छोड़ दो, वह तुम्हें संभाल लेंगे। 💙",
    "जहाँ भरोसा कृष्ण पर हो, वहाँ डर कभी टिकता नहीं। ✨",
    "कृष्ण का नाम ही हर समस्या का समाधान है। 🦚",
    "जो हुआ अच्छा हुआ, जो हो रहा है कृष्ण की इच्छा से हो रहा है। 🌿",
    "कृष्ण की शरण में गए तो फिर किसी सहारे की ज़रूरत नहीं। 🕊️",
    "हर टूटे दिल की दवा सिर्फ एक — श्रीकृष्ण। ❤️",
    "कृष्ण ने संभाल लिया, अब मुझे किसी बात का डर नहीं। 🌙",
    "कृष्ण चुप रहते हैं, लेकिन कभी गलत नहीं करते। 🔱",
]

# ------------- GEMINI SETUP ------------- #

def setup_gemini() -> genai.GenerativeModel:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found in environment.")

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(MODEL_NAME)

# ------------- STATE HELPERS ------------- #

def load_used_lines() -> Set[str]:
    os.makedirs(STATE_DIR, exist_ok=True)
    if not os.path.exists(STATE_FILE):
        # seed with examples so we always get NEW lines
        return set(STYLE_EXAMPLES)
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # merge with examples
        return set(data) | set(STYLE_EXAMPLES)
    except Exception:
        return set(STYLE_EXAMPLES)

def save_used_lines(lines: Set[str]) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(lines)), f, ensure_ascii=False, indent=2)
    except Exception:
        # If saving fails we still continue, just no long-term dedupe.
        pass

# ------------- TEXT CLEANING ------------- #

def is_hindi(text: str) -> bool:
    # Check if there is at least one Devanagari character
    return any("\u0900" <= ch <= "\u097F" for ch in text)

def clean_line(raw: str) -> str:
    if not raw:
        return ""
    # Take only first line
    text = raw.strip().split("\n")[0]
    # Remove extra quotes, bullets etc.
    for ch in ['"', "“", "”", "'", "‘", "’", "-", "•"]:
        if text.startswith(ch):
            text = text[1:].strip()
        if text.endswith(ch):
            text = text[:-1].strip()
    # Collapse spaces
    text = " ".join(text.split())
    return text

def ensure_emoji(text: str) -> str:
    # If already has one of our emojis, keep it
    if any(e in text for e in EMOJIS):
        return text
    # Otherwise, append 1–2 random emojis
    extra = "".join(random.sample(EMOJIS, k=2))
    # If sentence already ends with punctuation, just add emojis
    if text.endswith(("।", ".", "!", "…")):
        return f"{text} {extra}"
    else:
        return f"{text}। {extra}"

# ------------- GEMINI GENERATION ------------- #

def generate_deep_krishna_line(model: genai.GenerativeModel,
                               used: Set[str],
                               max_attempts: int = 8) -> str:
    """
    Ask Gemini for a short deep Hindi Krishna line with emojis,
    avoiding duplicates.
    """

    prompt = f"""
आप एक Instagram Reels कंटेंट राइटर हैं।
आपका काम सिर्फ एक लाइन लिखना है — छोटी, गहरी, पॉज़िटिव, और पूरी तरह भगवान श्रीकृष्ण पर केंद्रित।

सख्त नियम:
- भाषा: केवल हिंदी (देवनागरी में लिखो, अंग्रेज़ी शब्द नहीं)
- लंबाई: 8 से 16 शब्द
- टोन: शांत, भरोसा, surrender, care, सुरक्षा, प्रेम
- स्टाइल: simple, direct, relatable (लोग तुरंत connect करें)
- कंटेंट: भगवान श्रीकृष्ण को center में रखो (नाम ज़रूर आए — कृष्ण / श्रीकृष्ण / कान्हा / गोविंद आदि)
- आउटपुट: सिर्फ एक लाइन, कोई extra टेक्स्ट, कोई explanation नहीं
- प्यारे इमोजी include कर सकते हो जैसे: {", ".join(EMOJIS)}
- लाइन motivational या healing लगे, over dramatic नहीं

स्टाइल के उदाहरण (इन जैसी vibe, पर एकदम नई लाइन):
1. "जब सब छूट जाए, तब भी श्रीकृष्ण साथ रहते हैं। ❤️"
2. "जिसने कृष्ण को पाया, उसने सब कुछ पा लिया। 🌸"
3. "कृष्ण पर छोड़ दो, वह तुम्हें संभाल लेंगे। 💙"
4. "जहाँ भरोसा कृष्ण पर हो, वहाँ डर कभी टिकता नहीं। ✨"
5. "कृष्ण की शरण में गए तो फिर किसी सहारे की ज़रूरत नहीं। 🕊️"

अब इन्हें ध्यान से पढ़कर, इन्हीं की तरह स्टाइल रखते हुए,
एक नई, यूनिक, गहरी, छोटी हिंदी लाइन लिखो।
"""

    attempts = 0
    seen_this_call: Set[str] = set()

    while attempts < max_attempts:
        attempts += 1
        print(f"👉 Gemini attempt {attempts}...")

        try:
            response = model.generate_content(prompt)
            raw_text = getattr(response, "text", None)
        except Exception as e:
            print(f"   Gemini error: {e}")
            continue

        if not raw_text:
            print("   Empty response, retrying...")
            continue

        line = clean_line(raw_text)
        print(f"   Candidate: {line}")

        # Basic quality filters
        if not line:
            print("   Rejected: empty after cleaning.")
            continue

        if not is_hindi(line):
            print("   Rejected: not detected as Hindi.")
            continue

        words = line.split()
        if not (8 <= len(words) <= 16):
            print(f"   Rejected: {len(words)} words (needs 8–16).")
            continue

        # Add emojis if needed
        line = ensure_emoji(line)

        # Dedupe across previous runs + this run
        if line in used or line in seen_this_call:
            print("   Rejected: duplicate line.")
            continue

        # Accept
        seen_this_call.add(line)
        used.add(line)
        save_used_lines(used)
        print(f"   ✅ Final chosen line: {line}")
        return line

    # Fallback: if Gemini keeps failing, pick a random style example
    print("⚠️ Using fallback style example (Gemini failed too many times).")
    fallback = random.choice(STYLE_EXAMPLES)
    # Make sure fallback has emoji
    fallback = ensure_emoji(clean_line(fallback))
    used.add(fallback)
    save_used_lines(used)
    return fallback

# ------------- IMAGE / TEXT RENDERING ------------- #

def load_krishna_image() -> Image.Image:
    # Pick a random image from IMAGES_DIR
    files = [
        f for f in os.listdir(IMAGES_DIR)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]
    if not files:
        raise RuntimeError(f"No images found in {IMAGES_DIR}/")

    choice = random.choice(files)
    path = os.path.join(IMAGES_DIR, choice)
    print(f"🎨 Picking Krishna image: {path}")
    base = Image.open(path).convert("RGB")
    return base

def load_devanagari_font(size: int) -> ImageFont.FreeTypeFont:
    """
    Try to load a Devanagari-supporting font on Ubuntu runner.
    Fallback to default PIL font if nothing found.
    """
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    print("⚠️ Devanagari font not found, using default font.")
    return ImageFont.load_default()

def create_canvas_with_image(base_img: Image.Image,
                             size=(1080, 1920)) -> Image.Image:
    canvas = Image.new("RGB", size, color=(0, 0, 0))
    bw, bh = base_img.size
    cw, ch = size

    # scale image to fit height while keeping aspect
    scale = min(cw / bw, ch / bh)
    new_w = int(bw * scale)
    new_h = int(bh * scale)
    resized = base_img.resize((new_w, new_h), Image.LANCZOS)

    x = (cw - new_w) // 2
    y = (ch - new_h) // 2
    canvas.paste(resized, (x, y))
    return canvas

def draw_centered_text(canvas: Image.Image, text: str) -> Image.Image:
    draw = ImageDraw.Draw(canvas)
    cw, ch = canvas.size

    font = load_devanagari_font(size=52)

    # wrap text in multiple lines
    max_width = int(cw * 0.8)

    def text_size(t: str):
        return draw.textbbox((0, 0), t, font=font)

    # simple word wrap
    words = text.split()
    lines: List[str] = []
    current: List[str] = []
    for w in words:
        test = " ".join(current + [w])
        bbox = text_size(test)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            current.append(w)
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))

    line_height = (text_size("हिन्दी")[3] - text_size("हिन्दी")[1]) + 10
    total_height = line_height * len(lines)

    # place text around 70% height (little above bottom)
    y_start = int(ch * 0.70 - total_height / 2)

    # semi-transparent box behind text for readability
    padding_x = 40
    padding_y = 20
    min_x = cw
    max_x = 0
    for line in lines:
        bbox = text_size(line)
        w = bbox[2] - bbox[0]
        min_x = min(min_x, (cw - w) // 2)
        max_x = max(max_x, (cw + w) // 2)
    box_top = y_start - padding_y
    box_bottom = y_start + total_height + padding_y
    draw.rectangle(
        [(min_x - padding_x, box_top),
         (max_x + padding_x, box_bottom)],
        fill=(0, 0, 0, 180)
    )

    # draw each line
    y = y_start
    for line in lines:
        bbox = text_size(line)
        w = bbox[2] - bbox[0]
        x = (cw - w) // 2
        draw.text((x, y), line, font=font, fill=(255, 255, 255))
        y += line_height

    return canvas

# ------------- MAIN ENTRY ------------- #

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("🕉️ Loading Gemini model...")
    model = setup_gemini()

    print("📜 Loading used lines state...")
    used_lines = load_used_lines()

    print("🕉️ Generating deep Krishna Hindi line...")
    line = generate_deep_krishna_line(model, used_lines)
    print(f"✅ Final reel line: {line}")

    print("🎨 Loading Krishna image...")
    base_img = load_krishna_image()

    print("🖼️ Creating canvas and drawing text...")
    canvas = create_canvas_with_image(base_img)
    canvas = draw_centered_text(canvas, line)

    # Save under several common names so video step can find it
    for name in OUTPUT_FRAME_NAMES:
        out_path = os.path.join(OUTPUT_DIR, name)
        canvas.save(out_path, format="PNG")
        print(f"💾 Saved frame: {out_path}")

    print("✨ Image + text frame ready.")

if __name__ == "__main__":
    main()
