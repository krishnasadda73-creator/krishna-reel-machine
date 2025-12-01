import os
import random
from PIL import Image, ImageDraw, ImageFont
import textwrap
import google.generativeai as genai

# =========================
# CONFIG
# =========================
IMAGE_FOLDER = "images"
OUTPUT_FOLDER = "output"
OUTPUT_IMAGE = os.path.join(OUTPUT_FOLDER, "frame.png")
FONT_PATH = "fonts/NotoSansDevanagari-Regular.ttf"
FONT_SIZE = 64
MAX_TEXT_WIDTH = 900

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# =========================
# GEMINI SETUP
# =========================
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("models/gemini-1.5-flash")

# =========================
# GENERATE KRISHNA HINDI LINE
# =========================
def generate_krishna_line():
    prompt = """
Write one deep, positive, spiritual Hindi quote about Lord Krishna.
Rules:
- Only Hindi
- No English
- No emojis
- 1 or 2 short lines only
- Must feel peaceful, devotional and powerful
"""

    response = model.generate_content(prompt)
    text = response.text.strip()
    return text

# =========================
# PICK RANDOM IMAGE
# =========================
def pick_random_image():
    images = [f for f in os.listdir(IMAGE_FOLDER) if f.lower().endswith(("png", "jpg", "jpeg"))]
    if not images:
        raise Exception("❌ No images found in images folder")
    chosen = random.choice(images)
    print("🖼 Using Krishna image:", chosen)
    return os.path.join(IMAGE_FOLDER, chosen)

# =========================
# DRAW CENTERED TEXT
# =========================
def draw_centered_text(image, text):
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    lines = textwrap.wrap(text, width=20)
    total_height = sum(draw.textbbox((0, 0), line, font=font)[3] for line in lines)

    y = (image.height - total_height) // 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (image.width - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, font=font, fill="white", stroke_width=3, stroke_fill="black")
        y += bbox[3]

    return image

# =========================
# MAIN
# =========================
def main():
    print("🎨 Picking Krishna image...")
    img_path = pick_random_image()

    print("🕉 Generating Krishna Hindi Quote via Gemini...")
    line = generate_krishna_line()
    print("📜 Quote:", line)

    print("🖼 Creating 1080x1920 reel frame...")
    base_img = Image.open(img_path).convert("RGB")
    base_img = base_img.resize((1080, 1920))

    final_img = draw_centered_text(base_img, line)
    final_img.save(OUTPUT_IMAGE)

    print("✅ Image created:", OUTPUT_IMAGE)

if __name__ == "__main__":
    main()
