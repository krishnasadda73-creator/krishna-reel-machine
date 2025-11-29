import os
import random
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from generate_text import generate_unique_krishna_line

IMAGES_DIR = Path("images")
OUTPUT_DIR = Path("output")
STATE_DIR = Path("state")
USED_IMAGES_FILE = STATE_DIR / "used_images.json"

# ---------------- IMAGE STATE ----------------

def load_used_images():
    if not USED_IMAGES_FILE.exists():
        return []
    try:
        with open(USED_IMAGES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_used_images(names):
    STATE_DIR.mkdir(exist_ok=True)
    with open(USED_IMAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(names, f, ensured_ascii=False, indent=2)

def pick_image():
    all_files = [p for p in IMAGES_DIR.iterdir() if p.suffix.lower() in {".jpg", ".png", ".jpeg"}]
    used = load_used_images()
    unused = [p for p in all_files if p.name not in used]

    if not unused:
        used = []
        unused = all_files

    chosen = random.choice(unused)
    used.append(chosen.name)
    save_used_images(used)
    return chosen

# ---------------- TEXT HELPERS ----------------

def get_font(size):
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)

def wrap_text(text, font, max_width, draw):
    words = text.split()
    lines = []
    current = ""

    for w in words:
        test = (current + " " + w).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        width = bbox[2] - bbox[0]

        if width <= max_width:
            current = test
        else:
            lines.append(current)
            current = w

    if current:
        lines.append(current)

    return "\n".join(lines)

# ---------------- CANVAS & TEXT ----------------

def create_canvas_with_image(img_path):
    base = Image.new("RGB", (1080, 1920), (0, 0, 0))
    img = Image.open(img_path).convert("RGB")

    img_ratio = img.width / img.height
    target_ratio = 1080 / 1920

    if img_ratio > target_ratio:
        new_width = 1080
        new_height = int(new_width / img_ratio)
    else:
        new_height = 1920
        new_width = int(new_height * img_ratio)

    img = img.resize((new_width, new_height), Image.LANCZOS)

    x = (1080 - new_width) // 2
    y = (1920 - new_height) // 2
    base.paste(img, (x, y))

    return base

def draw_centered_text(canvas, text):
    draw = ImageDraw.Draw(canvas)
    W, H = canvas.size

    font_size = 72
    font = get_font(font_size)
    max_width = int(W * 0.8)

    wrapped = wrap_text(text, font, max_width, draw)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font)
    text_h = bbox[3] - bbox[1]

    x = W // 2
    y = int(H * 0.45)

    # Shadow
    draw.multiline_text((x+2, y+2), wrapped, font=font, fill="black", anchor="mm", align="center")
    draw.multiline_text((x, y), wrapped, font=font, fill="white", anchor="mm", align="center")

    return canvas

# ---------------- MAIN ----------------

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("🎨 Picking Krishna image...")
    img_path = pick_image()
    print("Selected:", img_path)

    print("🕉️ Generating Krishna line...")
    line = generate_unique_krishna_line()
    if not line:
        line = "In Krishna's embrace, your heart is always safe."

    print("Caption:", line)

    print("🖼 Creating final image...")
    canvas = create_canvas_with_image(img_path)
    canvas = draw_centered_text(canvas, line)

    out_path
