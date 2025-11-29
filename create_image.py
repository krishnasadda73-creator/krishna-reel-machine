import os
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from google import generativeai as gen

# ---------- Paths & constants ----------

ROOT = Path(__file__).parent
IMAGES_DIR = ROOT / "images"
OUTPUT_DIR = ROOT / "output"
STATE_DIR = ROOT / "state"

OUTPUT_DIR.mkdir(exist_ok=True)
STATE_DIR.mkdir(exist_ok=True)

USED_LINES_PATH = STATE_DIR / "used_lines.json"
USED_IMAGES_PATH = STATE_DIR / "used_images.json"

GEMINI_MODEL_NAME = "models/gemini-2.5-flash"

TARGET_W = 1080
TARGET_H = 1920


# ---------- Small helpers ----------

def load_json(path: Path, default):
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------- Unique image selection ----------

def pick_unique_image() -> Path:
    all_images = sorted(
        [p for p in IMAGES_DIR.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"}]
    )
    if not all_images:
        raise RuntimeError(f"No images found in {IMAGES_DIR}")

    used_images = load_json(USED_IMAGES_PATH, [])

    available = [p for p in all_images if p.name not in used_images]
    if not available:
        used_images = []
        available = all_images

    chosen = random.choice(available)
    used_images.append(chosen.name)
    save_json(USED_IMAGES_PATH, used_images)

    print(f"🖼️ Using Krishna image: {chosen}")
    return chosen


# ---------- Gemini caption generation ----------

def configure_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment.")
    gen.configure(api_key=api_key)


def clean_line(text: str) -> str:
    text = text.strip().replace("\n", " ")
    if text.startswith(("\"", "“", "‘")) and len(text) > 2:
        text = text[1:]
    if text.endswith(("\"", "”", "’")) and len(text) > 2:
        text = text[:-1]
    while "  " in text:
        text = text.replace("  ", " ")
    return text.strip()


def generate_unique_krishna_line(max_attempts: int = 8) -> str:
    configure_gemini()

    used_lines = load_json(USED_LINES_PATH, [])
    used_lower = {s.lower() for s in used_lines}

    prompt = """
You write short, deep, positive one-line reflections about Lord Krishna.

Rules:
- 1 single sentence only.
- Max 14 words.
- Must mention "Krishna" or clearly refer to Him as "He".
- Tone: comforting, devotional, grateful, hopeful.
- No hashtags, no emojis, no quote marks.
Return ONLY the sentence.
""".strip()

    model = gen.GenerativeModel(GEMINI_MODEL_NAME)

    for attempt in range(1, max_attempts + 1):
        print(f"🕉️ Gemini attempt {attempt}...")
        try:
            resp = model.generate_content(prompt)

            text = getattr(resp, "text", None)
            if not text and resp.candidates:
                parts = resp.candidates[0].content.parts
                text = "".join(getattr(p, "text", "") for p in parts)

            if not text:
                print("   ⚠️ Empty response, retrying...")
                continue

            line = clean_line(text)
            print(f"   Candidate: {line}")

            if not line:
                print("   ⚠️ Line empty after cleaning, skip.")
                continue

            if len(line.split()) > 14:
                print("   ⚠️ Too long, skip.")
                continue

            if "krishna" not in line.lower() and "he " not in line.lower():
                print("   ⚠️ Does not clearly refer to Krishna, skip.")
                continue

            if line.lower() in used_lower:
                print("   ⚠️ Duplicate line, skip.")
                continue

            used_lines.append(line)
            used_lines = used_lines[-500:]
            save_json(USED_LINES_PATH, used_lines)

            print(f"✅ Final line: {line}")
            return line

        except Exception as e:
            print(f"   ⚠️ Error from Gemini: {e}")

    fallback = "He knows your heart; trust Krishna with what you cannot see."
    print(f"⚠️ Using fallback line: {fallback}")
    return fallback


# ---------- Text placement logic ----------

def smart_text_y_on_image(canvas: Image.Image, box):
    x0, y0, x1, y1 = box
    img_crop = canvas.crop(box).convert("L")
    arr = np.array(img_crop)

    h, w = arr.shape

    zones = {
        "top": arr[0:int(h * 0.25), :],
        "middle": arr[int(h * 0.38):int(h * 0.63), :],
        "bottom": arr[int(h * 0.75):h, :],
    }

    scores = {name: np.mean(zone) for name, zone in zones.items()}
    darkest = min(scores, key=scores.get)

    if darkest == "top":
        local_y = int(h * 0.20)
    elif darkest == "middle":
        local_y = int(h * 0.50)
    else:
        local_y = int(h * 0.80)

    return y0 + local_y


def load_font(size: int) -> ImageFont.FreeTypeFont:
    # GitHub runner has DejaVuSans installed
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size=size)

    try:
        return ImageFont.truetype("arial.ttf", size=size)
    except Exception:
        return ImageFont.load_default()


def wrap_line(text: str, draw: ImageDraw.ImageDraw, font, max_width: int):
    words = text.split()
    if not words:
        return [""]

    lines = []
    current = words[0]
    for w in words[1:]:
        test = current + " " + w
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_width:
            current = test
        else:
            lines.append(current)
            current = w
    lines.append(current)

    if len(lines) > 2:
        first = " ".join(lines[:-1])
        second = lines[-1]
        lines = [first, second]

    return lines


def draw_elegant_text(canvas: Image.Image, text: str, image_box):
    draw = ImageDraw.Draw(canvas)

    base_size = 60
    if len(text) > 70:
        base_size = 52
    font = load_font(base_size)

    x0, y0, x1, y1 = image_box
    inner_margin_x = int((x1 - x0) * 0.06)
    inner_width = (x1 - x0) - 2 * inner_margin_x

    lines = wrap_line(text, draw, font, inner_width)

    line_heights = []
    line_widths = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_widths.append(bbox[2])
        line_heights.append(bbox[3] - bbox[1])

    total_h = sum(line_heights) + (len(lines) - 1) * 10
    center_y = smart_text_y_on_image(canvas, image_box)
    start_y = center_y - total_h // 2

    for i, line in enumerate(lines):
        w = line_widths[i]
        h = line_heights[i]
        x = (TARGET_W - w) // 2
        y = start_y + i * (h + 10)

        draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 220))   # shadow
        draw.text((x, y), line, font=font, fill=(255, 255, 255))         # main

    return canvas


# ---------- Frame creation ----------

def create_frame(image_path: Path, line: str) -> Path:
    img = Image.open(image_path).convert("RGB")

    canvas = Image.new("RGB", (TARGET_W, TARGET_H), (0, 0, 0))

    img_ratio = img.width / img.height
    target_ratio = TARGET_W / TARGET_H

    if img_ratio > target_ratio:
        new_w = TARGET_W
        new_h = int(TARGET_W / img_ratio)
    else:
        new_h = TARGET_H
        new_w = int(TARGET_H * img_ratio)

    img_resized = img.resize((new_w, new_h), Image.LANCZOS)
    offset_x = (TARGET_W - new_w) // 2
    offset_y = (TARGET_H - new_h) // 2

    canvas.paste(img_resized, (offset_x, offset_y))
    image_box = (offset_x, offset_y, offset_x + new_w, offset_y + new_h)

    print(f"📝 Overlay text: {line}")
    canvas = draw_elegant_text(canvas, line, image_box)

    out_path = OUTPUT_DIR / "krishna_frame.png"
    canvas.save(out_path, format="PNG")
    print(f"✅ Saved frame to: {out_path}")

    return out_path


def main():
    print("🎬 Krishna frame generator starting...")

    img_path = pick_unique_image()
    line = generate_unique_krishna_line()
    create_frame(img_path, line)

    print("🎉 Frame generation complete.")


if __name__ == "__main__":
    main()
