from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from youtube_search import YouTubeSearchService, YtDlpSearchClient, DictFormatter
from youtube_transcribe import YouTubeTranscriptService, OpenAIWhisperClient, OpenAITranscribeConfig
from youtube_audio import YtDlpAudioClient


@dataclass
class IntelliTubeContext:
    search_service: YouTubeSearchService
    transcript_service: YouTubeTranscriptService
    transcript_cache_dir: Path
    manifest_dir: Path


def build_context(
    *,
    audio_cache_dir: str | Path = "cache/audio",
    transcript_cache_dir: str | Path = "cache/transcripts",
    manifest_dir: str | Path = "cache/manifests",
    transcribe_model: str = "whisper-1",
) -> IntelliTubeContext:
    transcript_cache_dir = Path(transcript_cache_dir).resolve()
    manifest_dir = Path(manifest_dir).resolve()
    manifest_dir.mkdir(parents=True, exist_ok=True)

    search_service = YouTubeSearchService(
        search_client=YtDlpSearchClient(),
        formatter=DictFormatter(),
        detail_client=None,
    )

    audio_client = YtDlpAudioClient(cache_dir=str(Path(audio_cache_dir).resolve()))
    transcriber = OpenAIWhisperClient(config=OpenAITranscribeConfig(model=transcribe_model))
    transcript_service = YouTubeTranscriptService(
        audio_client=audio_client,
        transcriber=transcriber,
        transcript_cache_dir=str(transcript_cache_dir),
    )

    return IntelliTubeContext(
        search_service=search_service,
        transcript_service=transcript_service,
        transcript_cache_dir=transcript_cache_dir,
        manifest_dir=manifest_dir,
    )
