import os
import random
from pathlib import Path
from typing import List

from PIL import Image, ImageDraw, ImageFont

# We import our Hindi line generator (already Hindi-only)
from generate_text import get_krishna_line

# Directories
IMAGES_DIR = Path("images")
OUTPUT_DIR = Path("output")
OUTPUT_PATH = OUTPUT_DIR / "frame.png"

# Canvas size (1080x1920 reel)
CANVAS_SIZE = (1080, 1920)

# Local Devanagari font inside repo
FONT_PATH = Path("fonts") / "NotoSansDevanagari-Regular.ttf"


def pick_random_image() -> Path:
    files: List[Path] = [
        p for p in IMAGES_DIR.iterdir()
        if p.suffix.lower() in {".png", ".jpg", ".jpeg"}
    ]
    if not files:
        raise RuntimeError("No images found in images/ folder.")
    choice = random.choice(files)
    print(f"🎨 Selected base image: {choice}")
    return choice


def get_font(size: int) -> ImageFont.FreeTypeFont:
    """
    Always try our own Hindi-capable font first.
    This fixes the 'square boxes' problem on GitHub runners.
    """
    # 1) Our bundled Devanagari font
    if FONT_PATH.exists():
        try:
            print(f"🧩 Using bundled font: {FONT_PATH}")
            return ImageFont.truetype(str(FONT_PATH), size=size)
        except Exception as e:
            print("⚠️ Failed to load bundled font, trying system fonts:", e)

    # 2) Fallback to some common system fonts (in case you run locally)
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansDevanagariUI-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                print(f"🧩 Using system font: {path}")
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue

    # 3) Last resort
    print("⚠️ Falling back to default font (may not support Hindi).")
    return ImageFont.load_default()


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.Draw) -> str:
    words = text.split()
    if not words:
        return ""
    lines = []
    current = words[0]
    for w in words[1:]:
        test = current + " " + w
        w_len = draw.textlength(test, font=font)
        if w_len <= max_width:
            current = test
        else:
            lines.append(current)
            current = w
    lines.append(current)
    return "\n".join(lines)


def draw_centered_text(canvas: Image.Image, text: str) -> Image.Image:
    draw = ImageDraw.Draw(canvas, "RGBA")
    W, H = canvas.size

    # Use bottom ~35% of the image for text
    margin_x = int(W * 0.08)
    bottom_height = int(H * 0.35)
    area_top = H - bottom_height
    area_bottom = H - int(H * 0.05)

    font = get_font(size=56)

    max_text_width = W - 2 * margin_x
    wrapped = wrap_text(text, font, max_text_width, draw)

    # Measure text block
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align="center")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x = (W - text_w) // 2
    y = area_top + (bottom_height - text_h) // 2

    # Background rectangle behind text
    pad = 40
    rect = (
        x - pad,
        y - pad,
        x + text_w + pad,
        y + text_h + pad,
    )
    draw.rectangle(rect, fill=(0, 0, 0, 160))  # semi-transparent black

    # White Hindi text
    draw.multiline_text((x, y), wrapped, font=font, fill=(255, 255, 255, 255), align="center")
    return canvas


def create_frame() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Base image
    img_path = pick_random_image()
    base = Image.open(img_path).convert("RGB")

    # 2) Create 1080x1920 canvas and fit image
    canvas = Image.new("RGB", CANVAS_SIZE, (0, 0, 0))
    base_ratio = base.width / base.height
    canvas_ratio = CANVAS_SIZE[0] / CANVAS_SIZE[1]

    if base_ratio > canvas_ratio:
        # Image is wider → fit by height
        new_height = CANVAS_SIZE[1]
        new_width = int(new_height * base_ratio)
    else:
        # Image is taller → fit by width
        new_width = CANVAS_SIZE[0]
        new_height = int(new_width / base_ratio)

    resized = base.resize((new_width, new_height), Image.LANCZOS)
    x = (CANVAS_SIZE[0] - new_width) // 2
    y = (CANVAS_SIZE[1] - new_height) // 2
    canvas.paste(resized, (x, y))

    # 3) Get Hindi Krishna line
    line = get_krishna_line()
    print(f"📝 Final line for overlay: {line}")

    # 4) Draw text overlay
    canvas = draw_centered_text(canvas, line)

    # 5) Save frame
    canvas.save(OUTPUT_PATH)
    print(f"✅ Saved frame to {OUTPUT_PATH}")
    return OUTPUT_PATH


def main():
    create_frame()


if __name__ == "__main__":
    main()
