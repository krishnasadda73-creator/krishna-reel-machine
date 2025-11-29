import os
import random
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai

# ------------- PATHS & CONSTANTS -------------

BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"
OUTPUT_DIR = BASE_DIR / "output"
STATE_DIR = BASE_DIR / "state"

USED_LINES_FILE = STATE_DIR / "used_lines.json"

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920

# Use a good Gemini model name that we know works
GEMINI_MODEL_NAME = "models/gemini-2.5-flash"

# ------------- HELPERS FOR DIRECTORIES & STATE -------------

def ensure_dirs():
    OUTPUT_DIR.mkdir(exist_ok=True)
    STATE_DIR.mkdir(exist_ok=True)

def load_used_lines():
    if USED_LINES_FILE.exists():
        try:
            with open(USED_LINES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return set(data)
        except Exception:
            pass
    return set()

def save_used_lines(lines_set):
    try:
        with open(USED_LINES_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(lines_set)), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Could not save used lines: {e}")

# ------------- GEMINI SETUP & PROMPT -------------

def setup_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found in environment.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(GEMINI_MODEL_NAME)

GEMINI_PROMPT = """
You are writing very short, deep one-line quotes about Lord Krishna.

Rules:
- Only 1 sentence.
- 8 to 14 words.
- Focus on faith, surrender, trust, gratitude, protection, peace.
- Tone: emotional, peaceful, devotional, comforting.
- No hashtags, no emojis, no quotes (" ") around the line.
- No references to social media, followers, or "today".
- English only.

Return only the line, nothing else.
"""

def generate_unique_krishna_line(max_attempts=8):
    """
    Call Gemini until we get a non-empty, not-duplicate line.
    """
    used = load_used_lines()
    model = setup_gemini()

    for attempt in range(1, max_attempts + 1):
        print(f"👉 Gemini attempt {attempt}...")
        try:
            resp = model.generate_content(GEMINI_PROMPT)
            # Safe way to get plain text from response:
            text = resp.candidates[0].content.parts[0].text.strip()
        except Exception as e:
            print(f"⚠️ Gemini error on attempt {attempt}: {e}")
            continue

        # Basic cleaning
        line = text.replace("\n", " ").strip()
        # Remove any surrounding quotes
        if line.startswith(("'", '"')) and line.endswith(("'", '"')) and len(line) > 2:
            line = line[1:-1].strip()

        print(f"   Candidate: {line!r}")

        # Skip if empty or duplicate
        if not line:
            continue
        if line in used:
            print("   ↪️ Already used, trying again.")
            continue

        # New good line
        used.add(line)
        save_used_lines(used)
        print(f"✅ Accepted line: {line!r}")
        return line

    print("❌ Could not get a fresh line from Gemini.")
    return None

# ------------- IMAGE / TEXT DRAWING -------------

def pick_random_image():
    if not IMAGES_DIR.exists():
        raise RuntimeError(f"Images folder not found: {IMAGES_DIR}")
    candidates = [p for p in IMAGES_DIR.iterdir() if p.suffix.lower() in [".png", ".jpg", ".jpeg"]]
    if not candidates:
        raise RuntimeError(f"No images found in {IMAGES_DIR}")
    chosen = random.choice(candidates)
    print(f"🎨 Using image: {chosen.name}")
    return chosen

def load_font(size):
    # Try DejaVuSans (present in GitHub runners)
    possible_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    # Fallback to default font
    print("⚠️ Could not find DejaVu font, using default.")
    return ImageFont.load_default()

def draw_text_bar(canvas, text):
    """
    Draws a semi-transparent dark bar at bottom with centered white text.
    """
    draw = ImageDraw.Draw(canvas, "RGBA")
    W, H = canvas.size

    # Bar geometry
    bar_height = int(H * 0.22)
    bar_top = H - bar_height
    bar_bottom = H

    # Draw translucent bar
    bar_color = (0, 0, 0, 180)  # almost black, semi-transparent
    draw.rectangle([(0, bar_top), (W, bar_bottom)], fill=bar_color)

    # Text wrapping
    font = load_font(52)
    max_width = int(W * 0.85)

    words = text.split()
    lines = []
    current = ""

    for word in words:
        test_line = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_width = bbox[2] - bbox[0]
        if line_width <= max_width:
            current = test_line
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    # Compute total text height
    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_heights.append(bbox[3] - bbox[1])
    total_text_height = sum(line_heights) + (len(lines) - 1) * 10

    start_y = bar_top + (bar_height - total_text_height) // 2

    # Draw each line centered
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        line_h = bbox[3] - bbox[1]
        x = (W - line_w) // 2
        y = start_y + sum(line_heights[:i]) + i * 10

        # Stroke (outline) first
        draw.text((x, y), line, font=font, fill="white",
                  stroke_width=3, stroke_fill="black")

def create_frame_with_text():
    ensure_dirs()

    # 1) Pick base image
    img_path = pick_random_image()
    base_img = Image.open(img_path).convert("RGB")

    # 2) Generate deep Krishna line
    print("🕉️ Generating deep Krishna line from Gemini...")
    line = generate_unique_krishna_line()
    if not line:
        raise RuntimeError("No line generated from Gemini – cannot continue.")

    # Save line for debug
    debug_txt = OUTPUT_DIR / "last_line.txt"
    with open(debug_txt, "w", encoding="utf-8") as f:
        f.write(line)
    print(f"📝 Saved text line to {debug_txt}")

    # 3) Create 1080x1920 canvas and paste image
    canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), color=(0, 0, 0))

    # Resize base image to fit (keeping aspect)
    img_aspect = base_img.width / base_img.height
    canvas_aspect = CANVAS_WIDTH / CANVAS_HEIGHT

    if img_aspect > canvas_aspect:
        # Image is wider → fit width
        new_width = CANVAS_WIDTH
        new_height = int(new_width / img_aspect)
    else:
        # Image is taller → fit height
        new_height = CANVAS_HEIGHT
        new_width = int(new_height * img_aspect)

    resized = base_img.resize((new_width, new_height), Image.LANCZOS)
    x = (CANVAS_WIDTH - new_width) // 2
    y = (CANVAS_HEIGHT - new_height) // 2
    canvas.paste(resized, (x, y))

    # 4) Draw text bar + text
    draw_text_bar(canvas, line)

    # 5) Save result
    out_path = OUTPUT_DIR / "krishna_frame.png"
    canvas.save(out_path, format="PNG")
    print(f"✅ Saved frame with text to: {out_path}")

    return out_path

def main():
    create_frame_with_text()

if __name__ == "__main__":
    main()
