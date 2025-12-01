import os
import random
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai

# ---------- CONFIG ----------
IMAGE_DIR = "images"
OUTPUT_DIR = "output"
FONT_PATH = "fonts/NotoSansDevanagari-Regular.ttf"
CANVAS_SIZE = (1080, 1920)

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------- GEMINI SETUP ----------
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-pro")

PROMPT = """
Generate one deep, positive, spiritual Hindi quote focused on Lord Krishna.
Short 1–2 lines only.
No emojis.
No repeats.
Pure devotional tone.
"""

def generate_krishna_line():
    response = model.generate_content(PROMPT)
    return response.text.strip()

# ---------- IMAGE PICKER ----------
def pick_image():
    images = [f for f in os.listdir(IMAGE_DIR) if f.endswith(".png")]
    return os.path.join(IMAGE_DIR, random.choice(images))

# ---------- TEXT DRAW ----------
def draw_text(image_path, text):
    img = Image.open(image_path).convert("RGB")
    img = img.resize(CANVAS_SIZE)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_PATH, 48)

    y = 1500
    for line in text.split("\n"):
        w, h = draw.textbbox((0, 0), line, font=font)[2:]
        draw.text(((1080 - w) / 2, y), line, fill="white", font=font)
        y += 70

    out_path = os.path.join(OUTPUT_DIR, "frame.png")
    img.save(out_path)
    return out_path

# ---------- MAIN ----------
def main():
    print("🎨 Picking Krishna image...")
    img = pick_image()
    print("🕉️ Generating Krishna Hindi Quote via Gemini...")
    text = generate_krishna_line()
    print("📜 Quote:", text)
    draw_text(img, text)
    print("✅ Image created successfully!")

if __name__ == "__main__":
    main()
