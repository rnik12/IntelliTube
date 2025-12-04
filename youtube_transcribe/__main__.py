import argparse
import json
import os

from youtube_audio import YtDlpAudioClient
from .clients import OpenAIWhisperClient, OpenAITranscribeConfig
from .service import YouTubeTranscriptService


def main() -> None:
    p = argparse.ArgumentParser(description="Get YouTube metadata + transcript as JSON.")
    p.add_argument("url", help="YouTube video URL or ID")
    p.add_argument("--audio-cache-dir", default="cache/audio", help="Audio cache folder (default: cache/audio)")
    p.add_argument("--transcript-cache-dir", default="cache/transcripts", help="Transcript cache folder (default: cache/transcripts)")
    p.add_argument("--model", default=os.getenv("INTELLITUBE_TRANSCRIBE_MODEL", "whisper-1"),
                   help="Transcription model (default: whisper-1; can be set via INTELLITUBE_TRANSCRIBE_MODEL)")
    p.add_argument("--force", action="store_true", help="Re-transcribe even if cached transcript exists")
    p.add_argument("--language", default=None, help="Optional language hint (e.g. en, hi)")
    p.add_argument("--prompt", default=None, help="Optional prompt to improve domain vocabulary")
    p.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = p.parse_args()

    audio_client = YtDlpAudioClient(cache_dir=args.audio_cache_dir)
    transcriber = OpenAIWhisperClient(config=OpenAITranscribeConfig(model=args.model))
    svc = YouTubeTranscriptService(
        audio_client=audio_client,
        transcriber=transcriber,
        transcript_cache_dir=args.transcript_cache_dir,
    )

    payload = svc.get_transcript_json(
        args.url,
        force=args.force,
        language=args.language,
        prompt=args.prompt,
    )

    if args.pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
