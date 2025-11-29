import os
import random
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from generate_text import generate_unique_krishna_line

# --- Paths & state files ---
IMAGES_DIR = Path("images")
OUTPUT_DIR = Path("output")
STATE_DIR = Path("state")

USED_IMAGES_FILE = STATE_DIR / "used_images.json"


def load_used_images():
    if not USED_IMAGES_FILE.exists():
        return []
    try:
        with open(USED_IMAGES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def save_used_images(names):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(USED_IMAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(names, f, ensure_ascii=False, indent=2)


def pick_image():
    if not IMAGES_DIR.exists():
        raise RuntimeError("images/ folder does not exist. Please upload some Krishna images.")

    all_files = [
        p for p in IMAGES_DIR.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    ]
    if not all_files:
        raise RuntimeError("No image files found in images/ folder.")

    used = load_used_images()
    unused = [p for p in all_files if p.name not in used]

    # if everything is used, reset
    if not unused:
        used = []
        unused = all_files

    chosen = random.choice(unused)
    used.append(chosen.name)
    save_used_images(used)
    return chosen


def get_font(size: int) -> ImageFont.FreeTypeFont:
    # Try common Linux font path first (GitHub runner)
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)

    # Fallback: PIL default
    return ImageFont.load_default()


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw):
    words = text.split()
    lines = []
    current = ""

    for w in words:
        test = (current + " " + w).strip()
        w_width, _ = draw.textsize(test, font=font)
        if w_width <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)

    return "\n".join(lines)


def create_canvas_with_image(img_path: Path, target_size=(1080, 1920)) -> Image.Image:
    base = Image.new("RGB", target_size, (0, 0, 0))

    img = Image.open(img_path).convert("RGB")

    # Fit image inside 1080x1920 with aspect ratio preserved
    img_ratio = img.width / img.height
    target_ratio = target_size[0] / target_size[1]

    if img_ratio > target_ratio:
        # image is wider → fit width
        new_width = target_size[0]
        new_height = int(new_width / img_ratio)
    else:
        # image is taller → fit height
        new_height = target_size[1]
        new_width = int(new_height * img_ratio)

    img = img.resize((new_width, new_height), Image.LANCZOS)

    # center the image
    x = (target_size[0] - new_width) // 2
    y = (target_size[1] - new_height) // 2
    base.paste(img, (x, y))

    return base


def draw_centered_text(canvas: Image.Image, text: str):
    draw = ImageDraw.Draw(canvas)
    W, H = canvas.size

    # Start with a big font and shrink if needed
    font_size = 72
    font = get_font(font_size)

    max_text_width = int(W * 0.8)  # 80% of width
    wrapped = wrap_text(text, font, max_text_width, draw)

    # If too tall, reduce font size a bit
    while True:
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align="center")
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        if text_w <= max_text_width and text_h <= int(H * 0.4):
            break
        font_size = int(font_size * 0.9)
        if font_size < 30:
            break
        font = get_font(font_size)
        wrapped = wrap_text(text, font, max_text_width, draw)

    # Position: slightly above vertical center
    x = W // 2
    y = int(H * 0.45)

    # Shadow + white text (like IG style)
    shadow_offset = 2
    for dx, dy in [(-shadow_offset, -shadow_offset),
                   (shadow_offset, -shadow_offset),
                   (-shadow_offset, shadow_offset),
                   (shadow_offset, shadow_offset)]:
        draw.multiline_text(
            (x + dx, y + dy),
            wrapped,
            font=font,
            fill=(0, 0, 0),
            anchor="mm",
            align="center",
        )

    draw.multiline_text(
        (x, y),
        wrapped,
        font=font,
        fill=(255, 255, 255),
        anchor="mm",
        align="center",
    )

    return canvas


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("🎨 Picking Krishna image...")
    img_path = pick_image()
    print(f"   Image chosen: {img_path}")

    print("🕉️ Generating deep Krishna line from Gemini...")
    line = generate_unique_krishna_line()
    if not line:
        # extra safety, should basically never happen now
        line = "In Krishna's embrace, your heart is always safe."
        print("⚠️ Caption was empty, using fallback:", line)

    print(f"   Line: {line}")

    print("🖼️ Creating 1080x1920 canvas with text overlay...")
    canvas = create_canvas_with_image(img_path)
    canvas = draw_centered_text(canvas, line)

    out_path = OUTPUT_DIR / "krishna_frame.png"
    canvas.save(out_path, format="PNG")
    print(f"\n✅ Saved final frame to: {out_path}")


if __name__ == "__main__":
    main()
