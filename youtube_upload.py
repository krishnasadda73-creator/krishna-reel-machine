import os
import sys
from pathlib import Path
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from generate_text import clean_text

ROOT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT_DIR / "output"
DATA_DIR = ROOT_DIR / "data"
LAST_LINE_FILE = DATA_DIR / "last_line.txt"


def load_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"❌ Missing environment variable: {name}")
        sys.exit(1)
    return value


def load_hindi_line() -> str:
    """
    Read the last Hindi line from data/last_line.txt.
    If missing, just return a generic line.
    """
    try:
        text = LAST_LINE_FILE.read_text(encoding="utf-8").strip()
        if text:
            return text
    except FileNotFoundError:
        pass

    return "कृष्ण पर भरोसा रखो, सब अच्छा होगा।"


def get_youtube_service():
    client_id = load_env("YT_CLIENT_ID")
    client_secret = load_env("YT_CLIENT_SECRET")
    refresh_token = load_env("YT_REFRESH_TOKEN")

    creds = Credentials(
        token=None,  # will be refreshed
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )

    # Force refresh so we have a valid access token
    request = Request()
    creds.refresh(request)

    return build("youtube", "v3", credentials=creds)


def find_latest_video() -> Path | None:
    """
    Try to find the newest .mp4 file.
    1) Prefer output/*.mp4
    2) Fallback: repo_root/*.mp4
    """
    candidates: list[Path] = []

    if OUTPUT_DIR.exists():
        candidates.extend(OUTPUT_DIR.glob("*.mp4"))

    candidates.extend(ROOT_DIR.glob("*.mp4"))

    if not candidates:
        return None

    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return latest


def upload_video(video_path: Path):
    if not video_path.exists():
        print(f"❌ Provided video path does not exist: {video_path}")
        print("🔍 Trying to auto-detect latest .mp4 instead...")
        auto = find_latest_video()
        if not auto:
            print("❌ No .mp4 file found in output/ or repo root.")
            sys.exit(1)
        print(f"✅ Found video: {auto}")
        video_path = auto

    service = get_youtube_service()

    hindi_line = load_hindi_line()
    clean_line = clean_text(hindi_line)

    # Simple title & description
    today = datetime.utcnow().strftime("%d %b %Y")
    title = f"{clean_line} | Krishna Shorts {today}"
    description = (
        f"{clean_line}\n\n"
        "जय श्री कृष्णा 🌸🦚\n"
        "#krishna #radheradhe #shorts"
    )

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "22",  # People & Blogs
            "tags": [
                "krishna",
                "bhakti",
                "motivation",
                "hindi quotes",
                "spiritual",
                "shorts",
            ],
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": True,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        chunksize=-1,
        resumable=True,
    )

    print(f"📤 Starting upload to YouTube with file: {video_path}")
    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload progress: {int(status.progress() * 100)}%")

    video_id = response.get("id")
    print(f"✅ Upload complete! Video ID: {video_id}")
    print(f"https://www.youtube.com/watch?v={video_id}")


def main():
    # If a path is passed AND exists, use it.
    # If it doesn't exist, we'll auto-detect inside upload_video().
    if len(sys.argv) > 1:
        video_path = Path(sys.argv[1])
    else:
        video_path = OUTPUT_DIR / "reel.mp4"

    upload_video(video_path)


if __name__ == "__main__":
    main()
