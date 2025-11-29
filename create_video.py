import random
import json
import subprocess
from pathlib import Path

# Paths
FRAME_FILE = Path("output/krishna_frame.png")
BGM_DIR = Path("bgm")
OUTPUT_DIR = Path("output")
STATE_DIR = Path("state")
USED_MUSIC_FILE = STATE_DIR / "used_music.json"


# ---------- MUSIC STATE (NO DUPLICATES) ----------

def load_used_music():
    if not USED_MUSIC_FILE.exists():
        return []
    try:
        with open(USED_MUSIC_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_used_music(names):
    STATE_DIR.mkdir(exist_ok=True)
    with open(USED_MUSIC_FILE, "w", encoding="utf-8") as f:
        json.dump(names, f, ensure_ascii=False, indent=2)


def pick_bgm():
    tracks = [
        p for p in BGM_DIR.iterdir()
        if p.suffix.lower() in {".mp3", ".wav", ".m4a"}
    ]
    if not tracks:
        raise SystemExit("❌ No BGM files found in bgm/ folder")

    used = load_used_music()
    unused = [p for p in tracks if p.name not in used]

    # If all used, reset so they cycle again
    if not unused:
        used = []
        unused = tracks

    chosen = random.choice(unused)
    used.append(chosen.name)
    save_used_music(used)
    return chosen


# ---------- RENDER VIDEO WITH FFMPEG ----------

def render_video(duration_seconds: int = 15):
    if not FRAME_FILE.exists():
        raise SystemExit(f"❌ Frame image not found: {FRAME_FILE}")

    OUTPUT_DIR.mkdir(exist_ok=True)

    bgm = pick_bgm()
    out_video = OUTPUT_DIR / "krishna_reel.mp4"

    cmd = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-i", str(FRAME_FILE),
        "-i", str(bgm),
        "-c:v", "libx264",
        "-t", str(duration_seconds),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        str(out_video),
    ]

    print("🎵 Using BGM:", bgm)
    print("🎬 Running ffmpeg command:")
    print(" ".join(cmd))

    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise SystemExit(f"❌ ffmpeg failed with code {result.returncode}")

    print("✅ Video saved at:", out_video)


if __name__ == "__main__":
    render_video()
