import os
import random
import json
from PIL import Image, ImageDraw, ImageFont

# --- Paths ---
IMAGE_DIR = "images"
OUTPUT_DIR = "output"
DATA_DIR = "data"

LAST_LINE_FILE = os.path.join(DATA_DIR, "last_line.txt")
USED_IMAGES_FILE = os.path.join(DATA_DIR, "used_images.json")
FONT_PATH = os.path.join("fonts", "NotoSansDevanagari-Regular.ttf")  # Hindi font

# --- Canvas settings ---
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
TEXT_BOX_MARGIN = 80  # margin left/right inside canvas
TEXT_BOTTOM_MARGIN = 260  # distance from bottom
TEXT_MAX_LINES = 3
FONT_SIZE = 64


def ensure_dirs():
    """Make sure output folder exists."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------- TEXT HELPERS ----------

def load_last_line() -> str:
    """Read the last generated Hindi line from file."""
    if not os.path.exists(LAST_LINE_FILE):
        raise FileNotFoundError(f"{LAST_LINE_FILE} not found. Run generate_text.py first.")
    with open(LAST_LINE_FILE, "r", encoding="utf-8") as f:
        line = f.read().strip()
    if not line:
        raise ValueError("last_line.txt is empty.")
    return line


def wrap_text(text: str, font: ImageFont.FreeTypeFont,
              max_width: int, draw: ImageDraw.ImageDraw):
    """
    Wrap Hindi text into multiple lines so that each line
    fits inside max_width.
    """
    words = text.split(" ")
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

    # Hard limit lines if needed
    if len(lines) > TEXT_MAX_LINES:
        lines = lines[:TEXT_MAX_LINES]

    return lines


# ---------- IMAGE MEMORY HELPERS ----------

def load_used_images():
    """Load list of already used image filenames from JSON."""
    if not os.path.exists(USED_IMAGES_FILE):
        return []
    try:
        with open(USED_IMAGES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def save_used_images(used_list):
    """Save updated used image list to JSON."""
    with open(USED_IMAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(used_list, f, ensure_ascii=False, indent=2)


def pick_unique_image() -> str:
    """
    Pick an image from IMAGE_DIR that has not been used yet.
    When all images are used, reset the list and start again.
    Returns the full path to the chosen image.
    """
    all_files = [
        f for f in os.listdir(IMAGE_DIR)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]
    if not all_files:
        raise FileNotFoundError(f"No images found in {IMAGE_DIR}")

    used = load_used_images()

    # Images that are not used yet
    available = [f for f in all_files if f not in used]

    # If everything has been used, reset
    if not available:
        print("✅ All images used once — resetting used_images.json")
        used = []
        available = all_files

    chosen = random.choice(available)
    print(f"🎨 Using Krishna image: {chosen}")

    # Update memory and save
    used.append(chosen)
    save_used_images(used)

    return os.path.join(IMAGE_DIR, chosen)


# ---------- DRAWING ----------

def create_canvas_with_image(img_path: str) -> Image.Image:
    """
    Create a 1080x1920 canvas with the Krishna image centered,
    keeping aspect ratio (no distortion).
    """
    base = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0))

    img = Image.open(img_path).convert("RGB")
    w, h = img.size

    # Scale to fit inside canvas while keeping aspect ratio
    ratio = min(CANVAS_WIDTH / w, CANVAS_HEIGHT / h)
    new_w = int(w * ratio)
    new_h = int(h * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    # Center on canvas
    offset_x = (CANVAS_WIDTH - new_w) // 2
    offset_y = (CANVAS_HEIGHT - new_h) // 2
    base.paste(img, (offset_x, offset_y))

    return base


def draw_text_box(canvas: Image.Image, line: str) -> Image.Image:
    """Draw the Hindi text in a semi-transparent box near the bottom."""
    draw = ImageDraw.Draw(canvas)

    # Load font
    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except OSError:
        # Fallback system font (in case font file missing)
        font = ImageFont.load_default()
        print("⚠️ Could not load Hindi font, using default.")

    max_text_width = CANVAS_WIDTH - 2 * TEXT_BOX_MARGIN

    # Wrap text
    wrapped_lines = wrap_text(line, font, max_text_width, draw)

    # Measure total text height
    line_heights = []
    max_line_width = 0
    for l in wrapped_lines:
        bbox = draw.textbbox((0, 0), l, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        max_line_width = max(max_line_width, w)
        line_heights.append(h)

    total_text_height = sum(line_heights) + (len(line_heights) - 1) * 10

    # Text box coordinates
    box_width = max_line_width + 40
    box_height = total_text_height + 40

    box_left = (CANVAS_WIDTH - box_width) // 2
    box_top = CANVAS_HEIGHT - TEXT_BOTTOM_MARGIN - box_height
    box_right = box_left + box_width
    box_bottom = box_top + box_height

    # Draw semi-transparent rectangle
    box_color = (0, 0, 0, 180)
    # Need RGBA for alpha rectangle
    if canvas.mode != "RGBA":
        canvas = canvas.convert("RGBA")
        draw = ImageDraw.Draw(canvas)

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [box_left, box_top, box_right, box_bottom],
        radius=30,
        fill=box_color,
    )
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    # Draw text line by line centered
    current_y = box_top + 20
    for i, l in enumerate(wrapped_lines):
        bbox = draw.textbbox((0, 0), l, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = CANVAS_WIDTH // 2 - w // 2
        draw.text((x, current_y), l, font=font, fill=(255, 255, 255, 255))
        current_y += h + 10

    # Convert back to RGB for video
    return canvas.convert("RGB")


def main():
    ensure_dirs()

    # 1) Get unique image
    img_path = pick_unique_image()

    # 2) Load Hindi line from previous step
    line = load_last_line()
    print(f"🕉️ Using Hindi line: {line}")

    # 3) Compose image
    canvas = create_canvas_with_image(img_path)
    canvas = draw_text_box(canvas, line)

    # 4) Save frame for video creator
    output_path = os.path.join(OUTPUT_DIR, "frame.png")
    canvas.save(output_path, format="PNG")
    print(f"✅ Saved Krishna frame with text to {output_path}")


if __name__ == "__main__":
    main()
