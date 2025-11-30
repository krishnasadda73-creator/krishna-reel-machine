import os
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Hindi line generator (Gemini) – we only call it if last_line.txt is missing/empty
from generate_text import generate_unique_krishna_line

# ---------- Paths & constants ----------

ROOT_DIR = Path(__file__).resolve().parent
IMAGES_DIR = ROOT_DIR / "images"
OUTPUT_DIR = ROOT_DIR / "output"
DATA_DIR = ROOT_DIR / "data"
STICKERS_DIR = ROOT_DIR / "stickers"

LAST_LINE_FILE = DATA_DIR / "last_line.txt"

TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920

DEVANAGARI_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
]

FONT_SIZE = 60
TEXT_BOX_HEIGHT = 260      # height of dark band at bottom
LINE_SPACING = 10          # spacing between wrapped lines


# ---------- Utility helpers ----------

def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_last_line() -> str:
    """
    Read last Hindi line from last_line.txt.
    If missing / empty, ask Gemini for a fresh one and save it.
    """
    ensure_dirs()

    if LAST_LINE_FILE.exists():
        text = LAST_LINE_FILE.read_text(encoding="utf-8").strip()
        if text:
            return text
        else:
            print("⚠️ last_line.txt is empty, generating a new line from Gemini...")
    else:
        print("⚠️ last_line.txt missing, generating a new line from Gemini...")

    line = generate_unique_krishna_line()
    LAST_LINE_FILE.write_text(line, encoding="utf-8")
    return line


def choose_font() -> ImageFont.ImageFont:
    for path in DEVANAGARI_FONT_CANDIDATES:
        if os.path.exists(path):
            print(f"📝 Using Devanagari font: {path}")
            return ImageFont.truetype(path, FONT_SIZE)
    print("⚠️ Devanagari font not found, using default (emoji may break)")
    return ImageFont.load_default()


def choose_random_image() -> Path:
    candidates = [
        p for p in IMAGES_DIR.iterdir()
        if p.suffix.lower() in [".jpg", ".jpeg", ".png"]
    ]
    if not candidates:
        raise FileNotFoundError(f"No images found in {IMAGES_DIR}")
    img_path = random.choice(candidates)
    print(f"🎨 Using Krishna image: {img_path.name}")
    return img_path


def create_base_canvas(image_path: Path) -> Image.Image:
    """
    Create a 1080x1920 black canvas and paste the Krishna image centered,
    scaled to cover.
    """
    base = Image.new("RGB", (TARGET_WIDTH, TARGET_HEIGHT), (0, 0, 0))
    img = Image.open(image_path).convert("RGB")

    scale = max(TARGET_WIDTH / img.width, TARGET_HEIGHT / img.height)
    new_size = (int(img.width * scale), int(img.height * scale))
    img = img.resize(new_size, Image.LANCZOS)

    x = (TARGET_WIDTH - img.width) // 2
    y = (TARGET_HEIGHT - img.height) // 2
    base.paste(img, (x, y))
    return base


# ---- text measurement helpers using textbbox (NOT textsize) ----

def get_text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont):
    """
    Measure text width/height using textbbox, which exists in new Pillow.
    """
    if not text:
        return 0, 0
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    return width, height


def wrap_text(text: str, font: ImageFont.ImageFont,
              max_width: int, draw: ImageDraw.ImageDraw) -> str:
    """
    Simple word wrap using textbbox so it works on GitHub Actions Pillow.
    """
    words = text.split()
    lines = []
    current = ""

    for w in words:
        test = (current + " " + w).strip()
        width, _ = get_text_size(draw, test, font)
        if width <= max_width or not current:
            current = test
        else:
            lines.append(current)
            current = w

    if current:
        lines.append(current)

    return "\n".join(lines)


def measure_multiline(text: str, font: ImageFont.ImageFont,
                      draw: ImageDraw.ImageDraw):
    """
    Replacement for multiline_textsize.
    Returns (width, height) calculated line by line.
    """
    if not text:
        return 0, 0

    lines = text.split("\n")
    max_w = 0
    total_h = 0
    for line in lines:
        w, h = get_text_size(draw, line, font)
        if w > max_w:
            max_w = w
        total_h += h + LINE_SPACING

    total_h -= LINE_SPACING  # remove last extra spacing
    return max_w, total_h


def draw_text_with_bg(canvas: Image.Image, text: str,
                      font: ImageFont.ImageFont):
    """
    Draw a semi-transparent dark band at the bottom,
    then draw wrapped Hindi text centered inside.
    Returns (canvas, (box_top, box_bottom)) so stickers can be placed near it.
    """
    canvas = canvas.convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    box_top = TARGET_HEIGHT - TEXT_BOX_HEIGHT
    box_bottom = TARGET_HEIGHT

    # Dark band overlay
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    o_draw = ImageDraw.Draw(overlay)
    o_draw.rectangle([(0, box_top), (TARGET_WIDTH, box_bottom)],
                     fill=(0, 0, 0, 160))
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    max_text_width = int(TARGET_WIDTH * 0.8)
    wrapped = wrap_text(text, font, max_text_width, draw)
    text_w, text_h = measure_multiline(wrapped, font, draw)

    x = (TARGET_WIDTH - text_w) // 2
    y = box_top + (TEXT_BOX_HEIGHT - text_h) // 2

    # Draw each line with a small shadow
    lines = wrapped.split("\n")
    current_y = y
    for line in lines:
        w, h = get_text_size(draw, line, font)
        line_x = (TARGET_WIDTH - w) // 2

        # shadow
        draw.text((line_x + 2, current_y + 2),
                  line, font=font, fill=(0, 0, 0, 255))
        # white text
        draw.text((line_x, current_y),
                  line, font=font, fill=(255, 255, 255, 255))

        current_y += h + LINE_SPACING

    return canvas, (box_top, box_bottom)


# ---------- Sticker / emoji image logic ----------

def load_sticker_paths():
    """
    Load PNG stickers from stickers/ folder.
    """
    if not STICKERS_DIR.exists():
        print(f"⚠️ Stickers folder not found: {STICKERS_DIR}")
        return []

    paths = [p for p in STICKERS_DIR.iterdir()
             if p.suffix.lower() == ".png"]
    if not paths:
        print(f"⚠️ No PNG stickers found in {STICKERS_DIR}")
    else:
        print("💖 Available stickers:")
        for p in paths:
            print("   -", p.name)
    return paths


def paste_stickers(canvas: Image.Image, text_band, sticker_paths):
    """
    Paste 2–3 random stickers near the text band (no duplicates).
    """
    if not sticker_paths:
        return canvas

    canvas = canvas.convert("RGBA")
    box_top, box_bottom = text_band

    # positions for up to 3 stickers
    positions = [
        (int(TARGET_WIDTH * 0.23), box_top + 40),
        (int(TARGET_WIDTH * 0.77), box_top + 40),
        (int(TARGET_WIDTH * 0.50), box_bottom - 70),
    ]

    chosen = random.sample(sticker_paths, k=min(3, len(sticker_paths)))

    for sticker_path, (cx, cy) in zip(chosen, positions):
        try:
            sticker = Image.open(sticker_path).convert("RGBA")
        except Exception as e:
            print(f"⚠️ Could not open sticker {sticker_path.name}: {e}")
            continue

        # Resize to max about 120px
        max_size = 120
        scale = max(
            sticker.width / max_size,
            sticker.height / max_size,
            1,
        )
        new_size = (int(sticker.width / scale), int(sticker.height / scale))
        sticker = sticker.resize(new_size, Image.LANCZOS)

        x = int(cx - sticker.width / 2)
        y = int(cy - sticker.height / 2)

        canvas.alpha_composite(sticker, (x, y))

    return canvas


# ---------- Main ----------

def main():
    print("🕉️ Creating Krishna frame (Hindi + emoji stickers)...")
    ensure_dirs()

    line = load_last_line()
    print("💬 Hindi line:", line)

    font = choose_font()
    image_path = choose_random_image()

    # Base Krishna image
    canvas = create_base_canvas(image_path)

    # Draw text band
    canvas, text_band = draw_text_with_bg(canvas, line, font)

    # Stickers
    sticker_paths = load_sticker_paths()
    canvas = paste_stickers(canvas, text_band, sticker_paths)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "frame.png"
    canvas.convert("RGB").save(out_path, format="PNG")
    print(f"✅ Saved frame with text + stickers to: {out_path}")


if __name__ == "__main__":
    main()
