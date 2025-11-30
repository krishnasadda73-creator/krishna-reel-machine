#!/usr/bin/env python3
"""
Upload a Krishna reel to YouTube Shorts.

Usage:
  python youtube_upload.py output/reel.mp4
  # or just:
  python youtube_upload.py
  (then it will use output/reel.mp4 by default)

Requires these env vars (set via GitHub Secrets in the workflow):
  YT_CLIENT_ID
  YT_CLIENT_SECRET
  YT_REFRESH_TOKEN

IMPORTANT:
  This script always sets selfDeclaredMadeForKids = False
  → videos will NOT be marked as "made for kids".
"""

import os
import sys
from pathlib import Path
from datetime import datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


def get_video_path() -> Path:
    """Get video path from CLI arg or use default output/reel.mp4."""
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
    else:
        p = Path("output/reel.mp4")

    if not p.is_file():
        print(f"❌ Video file not found: {p}")
        sys.exit(1)
    return p


def get_youtube_client():
    """Create authenticated YouTube client from env refresh token."""
    client_id = os.environ.get("YT_CLIENT_ID")
    client_secret = os.environ.get("YT_CLIENT_SECRET")
    refresh_token = os.environ.get("YT_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        print("❌ Missing YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN env vars")
        sys.exit(1)

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )

    return build("youtube", "v3", credentials=creds)


def build_metadata(video_path: Path) -> dict:
    """Build YouTube video metadata (title, description, status)."""

    today = datetime.utcnow().strftime("%d %b %Y")
    title = f"Jai Shree Krishna ✨ | कृष्ण भक्ति शॉर्ट्स | {today}"
    description = (
        "जय श्री कृष्णा 🌸🦚\n\n"
        "Daily Krishna motivation & bhakti reels.\n"
        "#krishna #jaishreekrishna #shorts"
    )

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "22",  # People & Blogs (good default for bhakti content)
        },
        "status": {
            "privacyStatus": "public",
            # 🔥 MAIN THING: This keeps video **NOT** marked as "Made for kids"
            "selfDeclaredMadeForKids": False,
        },
    }

    return body


def upload_video(youtube, video_path: Path):
    """Upload the reel to YouTube Shorts."""
    body = build_metadata(video_path)

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        chunksize=-1,
        resumable=True,
    )

    print(f"📤 Uploading to YouTube: {video_path} ...")

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    try:
        response = request.execute()
    except HttpError as e:
        print("❌ YouTube API error while uploading:")
        print(e)
        sys.exit(1)

    video_id = response.get("id")
    print("✅ Upload complete!")
    print(f"🔗 Watch here: https://www.youtube.com/watch?v={video_id}")


def main():
    video_path = get_video_path()
    youtube = get_youtube_client()
    upload_video(youtube, video_path)


if __name__ == "__main__":
    main()
