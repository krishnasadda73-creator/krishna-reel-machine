import os
import random
import textwrap
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai

# =========================
# CONFIG
# =========================
IMAGE_FOLDER = "images"
OUTPUT_FOLDER = "output"
OUTPUT_IMAGE = os.path.join(OUTPUT_FOLDER, "reel_frame.png")
FONT_PATH = "fonts/NotoSansDevanagari-Regular.ttf"
FONT_SIZE = 64

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# =========================
# GEMINI SETUP (AUTO MODEL PICK)
# =========================
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def get_best_available_model():
    print("🔍 Fetching available Gemini models...")
    models = genai.list_models()

    # Prefer fast + cheap models
    priority = [
        "models/gemini-2.0-flash",
        "models/gemini-2.5-flash",
        "models/gemini-flash-latest",
        "models/gemini-pro"
    ]

    available = [m.name for m in models]

    for preferred in priority:
        if preferred in available:
            print("✅ Using Gemini model:", preferred)
            return genai.GenerativeModel(preferred)

    # Fallback: use first available model
    print("⚠️ Using fallback model:", available[0])
    return genai.GenerativeModel(available[0])

model = get_best_available_model()

# =========================
# GENERATE KRISHNA HINDI LINE
# =========================
def generate_krishna_line():
    prompt = """
एक गहरी, सकारात्मक और शांत हिंदी पंक्ति लिखें जो श्रीकृष्ण पर पूर्ण भरोसा, शरण और निश्चिंतता को दिखाए।

नियम:
- सिर्फ हिंदी
- कोई इमोजी नहीं
- 1 या 2 छोटी पंक्तियाँ
- भाव: श्रद्धा, भरोसा, शांति, कृष्ण की शरण
- किसी पुराने वाक्य की कॉपी नहीं
"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        return " ".join(text.split())
    except Exception as e:
        print("⚠️ Gemini failed, using fallback text.")
        return "जब कृष्ण साथ हों, तो हर डर शांति में बदल जाता है।"

# =========================
# PICK RANDOM IMAGE
# =========================
def pick_random_image():
    images = [
        f for f in os.listdir(IMAGE_FOLDER)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]

    if not images:
        raise RuntimeError("❌ No images found in images/ folder")

    chosen = random.choice(images)
    print("🖼 Using Krishna image:", chosen)
    return os.path.join(IMAGE_FOLDER, chosen)

# =========================
# DRAW CENTERED TEXT
# =========================
def draw_centered_text(image, text):
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    lines = textwrap.wrap(text, width=18)

    heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        heights.append(bbox[3] - bbox[1])

    total_height = sum(heights) + (len(lines) - 1) * 12
    y = (image.height - total_height) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (image.width - w) // 2

        draw.text(
            (x, y),
            line,
            font=font,
            fill="white",
            stroke_width=3,
            stroke_fill="black",
        )

        y += heights[i] + 12

    return image

# =========================
# MAIN
# =========================
def main():
    print("🎨 Picking Krishna image...")
    img_path = pick_random_image()

    print("🕉 Generating Krishna Hindi Quote via Gemini...")
    text = generate_krishna_line()
    print("📜 Quote:", text)

    print("🖼 Creating 1080x1920 reel frame...")
    base_img = Image.open(img_path).convert("RGB")
    base_img = base_img.resize((1080, 1920))

    final = draw_centered_text(base_img, text)
    final.save(OUTPUT_IMAGE)

    print("✅ Frame created:", OUTPUT_IMAGE)

if __name__ == "__main__":
    main()
