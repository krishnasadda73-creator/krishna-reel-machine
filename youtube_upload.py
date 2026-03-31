#!/usr/bin/env python3
"""
Simple YouTube Shorts uploader (No ENV needed)

Usage:
  python youtube_upload.py output/reel.mp4
"""

import os
import sys
import pickle
from pathlib import Path
from datetime import datetime

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# 🔥 Required scope
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_video_path() -> Path:
    """Get video path from CLI arg or default."""
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
    else:
        p = Path("output/reel.mp4")

    if not p.is_file():
        print(f"❌ Video file not found: {p}")
        sys.exit(1)

    return p


def get_youtube_client():
    """Handle login + token storage."""
    creds = None

    # 🔹 Load existing token
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    # 🔹 If no valid creds → login
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            "client_secret.json", SCOPES
        )
        creds = flow.run_local_server(port=0)

        # Save token for future use
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)


def build_metadata():
    """Create title, description, etc."""
    today = datetime.utcnow().strftime("%d %b %Y")

    title = f"Jai Shree Krishna ✨ | Krishna Shorts | {today}"
    description = (
        "जय श्री कृष्णा 🌸🦚\n\n"
        "Daily Krishna reels 🙏\n"
        "#krishna #jaishreekrishna #shorts"
    )

    return {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "22",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }


def upload_video(youtube, video_path: Path):
    """Upload video to YouTube."""
    body = build_metadata()

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True
    )

    print(f"📤 Uploading: {video_path} ...")

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    try:
        response = request.execute()
        video_id = response.get("id")

        print("✅ Upload successful!")
        print(f"🔗 https://www.youtube.com/watch?v={video_id}")

    except HttpError as e:
        print("❌ Upload failed:")
        print(e)
        sys.exit(1)


def main():
    video_path = get_video_path()
    youtube = get_youtube_client()
    upload_video(youtube, video_path)


if __name__ == "__main__":
    main()
