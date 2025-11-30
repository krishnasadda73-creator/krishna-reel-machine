import os
import random
from pathlib import Path
from typing import Tuple, List

from PIL import Image, ImageDraw, ImageFont

from generate_text import get_krishna_line

IMAGES_DIR = Path("images")
OUTPUT_DIR = Path("output")
OUTPUT_PATH = OUTPUT_DIR / "frame.png"

CANVAS_SIZE = (1080, 1920)  # width, height


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
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansDevanagariUI-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
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

    # Area (bottom 35% of image)
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

    # Background rectangle
    pad = 40
    rect = (
        x - pad,
        y - pad,
        x + text_w + pad,
        y + text_h + pad,
    )
    # semi-transparent black
    draw.rectangle(rect, fill=(0, 0, 0, 160))

    # White text
    draw.multiline_text((x, y), wrapped, font=font, fill=(255, 255, 255, 255), align="center")
    return canvas


def create_frame() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1) base image
    img_path = pick_random_image()
    base = Image.open(img_path).convert("RGB")

    # 2) create canvas 1080x1920 and center-crop/fit
    canvas = Image.new("RGB", CANVAS_SIZE, (0, 0, 0))
    base_ratio = base.width / base.height
    canvas_ratio = CANVAS_SIZE[0] / CANVAS_SIZE[1]

    if base_ratio > canvas_ratio:
        # image is wider → fit by height
        new_height = CANVAS_SIZE[1]
        new_width = int(new_height * base_ratio)
    else:
        # image is taller → fit by width
        new_width = CANVAS_SIZE[0]
        new_height = int(new_width / base_ratio)

    resized = base.resize((new_width, new_height), Image.LANCZOS)
    x = (CANVAS_SIZE[0] - new_width) // 2
    y = (CANVAS_SIZE[1] - new_height) // 2
    canvas.paste(resized, (x, y))

    # 3) get Hindi Krishna line
    line = get_krishna_line()
    print(f"📝 Final line for overlay: {line}")

    # 4) draw text
    canvas = draw_centered_text(canvas, line)

    # 5) save
    canvas.save(OUTPUT_PATH)
    print(f"✅ Saved frame to {OUTPUT_PATH}")
    return OUTPUT_PATH


def main():
    create_frame()


if __name__ == "__main__":
    main()
