# create_image.py
import os
import random
from typing import Tuple, List

from PIL import Image, ImageDraw, ImageFont

from generate_text import get_final_line

IMAGES_DIR = "images"
OUTPUT_DIR = "output"
FONT_PATH = "fonts/NotoSansDevanagari-Bold.ttf"  # adjust if different

CANVAS_W = 1080
CANVAS_H = 1920
TEXT_MAX_WIDTH_RATIO = 0.78   # text width relative to canvas
TEXT_AREA_CENTER_Y_RATIO = 0.70  # where the block of text is vertically centered


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def pick_random_image() -> str:
    files = [
        f for f in os.listdir(IMAGES_DIR)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]
    if not files:
        raise RuntimeError(f"No images found in {IMAGES_DIR}/")
    chosen = random.choice(files)
    path = os.path.join(IMAGES_DIR, chosen)
    print(f"🎨 Selected Krishna image: {path}")
    return path


def load_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        print("⚠️ Could not load Devanagari font, using default.")
        return ImageFont.load_default()


def make_canvas_with_image(img_path: str) -> Image.Image:
    base = Image.open(img_path).convert("RGB")

    # scale to fit into 1080x1920 with letterbox
    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), color=(0, 0, 0))

    w, h = base.size
    scale = min(CANVAS_W / w, CANVAS_H / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    base = base.resize((new_w, new_h), Image.LANCZOS)

    offset_x = (CANVAS_W - new_w) // 2
    offset_y = (CANVAS_H - new_h) // 2
    canvas.paste(base, (offset_x, offset_y))

    return canvas


def wrap_text(text: str, font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw,
              max_width: int) -> List[str]:
    """
    Wrap text into multiple lines so each line fits max_width.
    """
    words = text.split()
    lines: List[str] = []
    current = ""

    for word in words:
        test = (current + " " + word).strip()
        w = draw.textlength(test, font=font)
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def draw_centered_text(canvas: Image.Image, text: str) -> Image.Image:
    if not text or not isinstance(text, str):
        text = "कृष्ण साथ हों तो सब सम्भव है। 🦚"

    draw = ImageDraw.Draw(canvas)

    # Start with big font and shrink until it fits nicely
    font_size = 64
    font = load_font(font_size)

    max_width = int(CANVAS_W * TEXT_MAX_WIDTH_RATIO)

    while True:
        lines = wrap_text(text, font, draw, max_width)
        line_height = font.getbbox("ह")[3] - font.getbbox("ह")[1]
        total_height = len(lines) * line_height + (len(lines) - 1) * 10

        if total_height < CANVAS_H * 0.35 and len(lines) <= 3:
            break
        font_size -= 4
        if font_size < 32:
            break
        font = load_font(font_size)

    # recalc with final font
    lines = wrap_text(text, font, draw, max_width)
    line_height = font.getbbox("ह")[3] - font.getbbox("ह")[1]
    total_height = len(lines) * line_height + (len(lines) - 1) * 10

    center_y = int(CANVAS_H * TEXT_AREA_CENTER_Y_RATIO)
    start_y = center_y - total_height // 2

    # Draw shadow + main text
    for i, line in enumerate(lines):
        w = draw.textlength(line, font=font)
        x = (CANVAS_W - w) // 2
        y = start_y + i * (line_height + 10)

        # subtle box behind text for readability
        padding_x = 24
        padding_y = 14
        box = [x - padding_x, y - padding_y,
               x + w + padding_x, y + line_height + padding_y]
        draw.rounded_rectangle(box, radius=20, fill=(0, 0, 0, 180))

        # shadow
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0))
        # main text
        draw.text((x, y), line, font=font, fill=(255, 255, 255))

    return canvas


def main():
    ensure_output_dir()

    img_path = pick_random_image()

    # get deep Hindi Krishna line
    line = get_final_line()
    print(f"🕉️ Final Hindi line: {line}")

    canvas = make_canvas_with_image(img_path)
    canvas = draw_centered_text(canvas, line)

    out_path = os.path.join(OUTPUT_DIR, "krishna_frame.png")
    canvas.save(out_path, format="PNG", quality=95)
    print(f"✅ Saved image with text overlay to: {out_path}")


if __name__ == "__main__":
    main()
