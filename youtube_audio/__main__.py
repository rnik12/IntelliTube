from __future__ import annotations
import argparse
from .clients import YtDlpAudioClient
from .service import YouTubeAudioService

def main() -> None:
    p = argparse.ArgumentParser(description="Download YouTube audio to cache/audio (with skipping).")
    p.add_argument("url", help="YouTube video URL or ID")
    p.add_argument("--cache-dir", default="cache/audio", help="Cache folder (default: cache/audio)")
    args = p.parse_args()

    svc = YouTubeAudioService(YtDlpAudioClient(cache_dir=args.cache_dir))
    path = svc.download_audio(args.url)
    print(path)

if __name__ == "__main__":
    main()
