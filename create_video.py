# create_video.py
import os
import random
from moviepy.editor import ImageClip, AudioFileClip

IMAGE_PATH = "output/krishna_frame.png"
BGM_DIR = "bgm"
OUTPUT_DIR = "output"
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "krishna_reel.mp4")

VIDEO_DURATION = 10  # seconds
FPS = 30


def pick_random_bgm():
    if not os.path.exists(BGM_DIR):
        raise RuntimeError("bgm folder not found!")

    files = [f for f in os.listdir(BGM_DIR) if f.lower().endswith(".mp3")]

    if not files:
        raise RuntimeError("No MP3 files found inside bgm folder!")

    chosen = random.choice(files)
    path = os.path.join(BGM_DIR, chosen)

    print(f"🎵 Selected BGM: {path}")
    return path


def main():
    if not os.path.exists(IMAGE_PATH):
        raise RuntimeError("Krishna frame not found! Run create_image.py first.")

    bgm_path = pick_random_bgm()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("🎬 Creating reel with image + random BGM...")

    image_clip = ImageClip(IMAGE_PATH).set_duration(VIDEO_DURATION)

    audio_clip = AudioFileClip(bgm_path)

    if audio_clip.duration > VIDEO_DURATION:
        audio_clip = audio_clip.subclip(0, VIDEO_DURATION)
    else:
        audio_clip = audio_clip.audio_loop(duration=VIDEO_DURATION)

    video = image_clip.set_audio(audio_clip)

    video.write_videofile(
        OUTPUT_PATH,
        codec="libx264",
        audio_codec="aac",
        fps=FPS,
        threads=4,
        verbose=False,
        logger=None
    )

    print("✅ FINAL REEL CREATED:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
