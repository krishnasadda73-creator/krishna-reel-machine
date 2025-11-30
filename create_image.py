import os
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Import the line generator from generate_text.py
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

# Try to use a Devanagari-capable font on GitHub runner
DEVANAGARI_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
]

FONT_SIZE = 60
TEXT_BOX_HEIGHT = 260   # bottom band height for text + stickers


# ---------- Helpers ----------

def ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_last_line() -> str:
    """
    Read the last generated Hindi line from data/last_line.txt.
    If file is missing or empty, call Gemini to generate a fresh line,
    save it, and return it.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not LAST_LINE_FILE.exists():
        print("⚠️ last_line.txt not found — generating a fresh line with Gemini...")
        line = generate_unique_krishna_line()
        LAST_LINE_FILE.write_text(line, encoding="utf-8")
        return line

    text = LAST_LINE_FILE.read_text(encoding="utf-8").strip()
    if not text:
        print("⚠️ last_line.txt is empty — generating a fresh line with Gemini...")
        line = generate_unique_krishna_line()
        LAST_LINE_FILE.write_text(line, encoding="utf-8")
        return line

    return text


def choose_font() -> ImageFont.FreeTypeFont:
    """Pick a Devanagari font if available, otherwise default."""
    for path in DEVANAGARI_FONT_CANDIDATES:
        if os.path.exists(path):
            print(f"📝 Using font: {path}")
            return ImageFont.truetype(path, FONT_SIZE)
    print("⚠️ Devanagari font not found, using default PIL font (may break Hindi)")
    return ImageFont.load_default()


def choose_random_image() -> Path:
    """Pick a random Krishna image from images/."""
    candidates = [p for p in IMAGES_DIR.iterdir()
                  if p.suffix.lower() in [".jpg", ".jpeg", ".png"]]
    if not candidates:
        raise FileNotFoundError(f"No images found in {IMAGES_DIR}")
    img_path = random.choice(candidates)
    print(f"🎨 Using image: {img_path.name}")
    return img_path


def wrap_text(text: str, font: ImageFont.FreeTypeFont,
              max_width: int, draw: ImageDraw.ImageDraw) -> str:
    """Simple word wrap for Hindi text within max_width."""
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = (current + " " + word).strip()
        w, _ = draw.textsize(test, font=font)
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return "\n".join(lines)


def create_base_canvas(image_path: Path) -> Image.Image:
    """Create 1080x1920 canvas and center the original image."""
    base = Image.new("RGB", (TARGET_WIDTH, TARGET_HEIGHT), (0, 0, 0))
    img = Image.open(image_path).convert("RGB")

    # Scale to cover 1080x1920
    scale = max(TARGET_WIDTH / img.width, TARGET_HEIGHT / img.height)
    new_size = (int(img.width * scale), int(img.height * scale))
    img = img.resize(new_size, Image.LANCZOS)

    # Center paste
    x = (TARGET_WIDTH - img.width) // 2
    y = (TARGET_HEIGHT - img.height) // 2
    base.paste(img, (x, y))

    return base


def draw_text_with_bg(canvas: Image.Image, text: str,
                      font: ImageFont.FreeTypeFont):
    """Draw semi-transparent band + centered Hindi text at bottom."""
    canvas = canvas.convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    # Bottom text box coordinates
    box_top = TARGET_HEIGHT - TEXT_BOX_HEIGHT
    box_bottom = TARGET_HEIGHT

    # Semi-transparent black rectangle
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(
        [(0, box_top), (TARGET_WIDTH, box_bottom)],
        fill=(0, 0, 0, 160),
    )
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    # Wrap text to fit within margins
    max_text_width = int(TARGET_WIDTH * 0.8)
    wrapped = wrap_text(text, font, max_text_width, draw)

    # Measure wrapped text block
    text_w, text_h = draw.multiline_textsize(wrapped, font=font, spacing=10)

    text_x = (TARGET_WIDTH - text_w) // 2
    text_y = box_top + (TEXT_BOX_HEIGHT - text_h) // 2

    # Draw text: dark shadow + white text
    shadow_offset = 2
    draw.multiline_text(
        (text_x + shadow_offset, text_y + shadow_offset),
        wrapped,
        font=font,
        fill=(0, 0, 0, 255),
        align="center",
        spacing=10,
    )
    draw.multiline_text(
        (text_x, text_y),
        wrapped,
        font=font,
        fill=(255, 255, 255, 255),
        align="center",
        spacing=10,
    )

    return canvas, (box_top, box_bottom)


# ---------- Sticker (emoji image) logic ----------

def load_sticker_paths():
    """Load all PNG stickers from stickers/."""
    if not STICKERS_DIR.exists():
        print(f"⚠️ Stickers folder not found: {STICKERS_DIR} (no emojis will be added)")
        return []

    paths = [p for p in STICKERS_DIR.iterdir() if p.suffix.lower() == ".png"]
    if not paths:
        print(f"⚠️ No PNG stickers found in {STICKERS_DIR} (no emojis will be added)")
    else:
        print("💖 Loaded stickers:")
        for p in paths:
            print("   -", p.name)
    return paths


def paste_stickers(canvas: Image.Image, text_band, sticker_paths):
    """
    Paste 2–3 random stickers (no duplicates) around the bottom text band.
    text_band = (box_top, box_bottom)
    """
    if not sticker_paths:
        return canvas

    canvas = canvas.convert("RGBA")
    box_top, box_bottom = text_band

    # Positions near the text box (left / right / above)
    positions = [
        (int(TARGET_WIDTH * 0.23), box_top + 40),
        (int(TARGET_WIDTH * 0.77), box_top + 40),
        (int(TARGET_WIDTH * 0.5),  box_bottom - 70),
    ]

    # Choose up to 3 distinct stickers
    chosen_stickers = random.sample(sticker_paths,
                                    k=min(3, len(sticker_paths)))

    for sticker_path, (x, y) in zip(chosen_stickers, positions):
        try:
            sticker = Image.open(sticker_path).convert("RGBA")
        except Exception as e:
            print(f"⚠️ Could not open sticker {sticker_path.name}: {e}")
            continue

        # Resize sticker to a nice size
        max_sticker_size = 120
        scale = max(
            sticker.width / max_sticker_size,
            sticker.height / max_sticker_size,
            1,
        )
        new_size = (int(sticker.width / scale), int(sticker.height / scale))
        sticker = sticker.resize(new_size, Image.LANCZOS)

        # Center sticker at (x, y)
        paste_x = int(x - sticker.width / 2)
        paste_y = int(y - sticker.height / 2)

        canvas.alpha_composite(sticker, (paste_x, paste_y))

    return canvas


# ---------- Main ----------

def main():
    print("🕉️ Creating Krishna frame (Hindi text + emoji stickers)...")
    ensure_output_dir()

    line = load_last_line()
    print("💬 Hindi line:", line)

    font = choose_font()
    image_path = choose_random_image()

    canvas = create_base_canvas(image_path)
    canvas, text_band = draw_text_with_bg(canvas, line, font)

    sticker_paths = load_sticker_paths()
    canvas = paste_stickers(canvas, text_band, sticker_paths)

    # Save final PNG
    output_path = OUTPUT_DIR / "frame.png"
    canvas.convert("RGB").save(output_path, format="PNG")
    print(f"✅ Saved frame with text + stickers to: {output_path}")


if __name__ == "__main__":
    main()
