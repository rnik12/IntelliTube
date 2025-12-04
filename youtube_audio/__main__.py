from __future__ import annotations
import argparse
import json
from .clients import YtDlpAudioClient
from .service import YouTubeAudioService


def main() -> None:
    p = argparse.ArgumentParser(description="Download YouTube audio to cache/audio (with skipping).")
    p.add_argument("url", help="YouTube video URL or ID")
    p.add_argument("--cache-dir", default="cache/audio", help="Cache folder (default: cache/audio)")
    p.add_argument("--info", action="store_true", help="Print title/description/path as JSON")
    args = p.parse_args()

    svc = YouTubeAudioService(YtDlpAudioClient(cache_dir=args.cache_dir))

    if args.info:
        info = svc.get_audio_info(args.url)
        print(json.dumps({
            "video_id": info.video_id,
            "title": info.title,
            "description": info.description,
            "audio_path": info.audio_path,
        }, ensure_ascii=False, indent=2))
    else:
        path = svc.download_audio(args.url)
        print(path)


if __name__ == "__main__":
    main()
