# create_video.py
import os

from moviepy.editor import ImageClip, AudioFileClip


IMAGE_PATH = "output/krishna_frame.png"
BGM_PATH = "bgm/flute.mp3"      # rename if your file is different
OUTPUT_DIR = "output"
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "krishna_reel.mp4")

VIDEO_DURATION = 10  # seconds
FPS = 30


def main():
    if not os.path.exists(IMAGE_PATH):
        raise RuntimeError(f"Image not found at {IMAGE_PATH}. "
                           f"Run create_image.py first.")

    if not os.path.exists(BGM_PATH):
        raise RuntimeError(f"BGM not found at {BGM_PATH}.")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("🎬 Creating reel video from frame + BGM...")

    image_clip = ImageClip(IMAGE_PATH).set_duration(VIDEO_DURATION)

    audio_clip = AudioFileClip(BGM_PATH)
    # Trim/loop audio to match duration
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
        logger=None,
    )

    print(f"✅ Reel created: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
