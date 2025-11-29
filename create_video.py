import random
import json
import subprocess
from pathlib import Path

OUTPUT_DIR = Path("output")
BGM_DIR = Path("bgm")
STATE_DIR = Path("state")
USED_MUSIC_FILE = STATE_DIR / "used_music.json"


# ---------- FIND LATEST IMAGE (AUTO) ----------

def find_latest_image():
    images = list(OUTPUT_DIR.glob("*.png"))
    if not images:
        raise SystemExit("❌ No PNG image found inside output/ folder")

    latest = max(images, key=lambda p: p.stat().st_mtime)
    print("🖼️ Using image:", latest)
    return latest


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

    if not unused:
        used = []
        unused = tracks

    chosen = random.choice(unused)
    used.append(chosen.name)
    save_used_music(used)

    return chosen


# ---------- CREATE VIDEO ----------

def render_video(duration_seconds=15):
    OUTPUT_DIR.mkdir(exist_ok=True)
    frame = find_latest_image()
    bgm = pick_bgm()

    out_video = OUTPUT_DIR / "krishna_reel.mp4"

    cmd = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-i", str(frame),
        "-i", str(bgm),
        "-c:v", "libx264",
        "-t", str(duration_seconds),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        str(out_video)
    ]

    print("🎵 Using BGM:", bgm.name)
    print("🎬 Creating video...")

    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise SystemExit("❌ ffmpeg failed")

    print("✅ Video created:", out_video)


if __name__ == "__main__":
    render_video()
