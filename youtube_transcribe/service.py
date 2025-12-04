from typing import Optional, Dict, Any
from dataclasses import asdict
from pathlib import Path
from datetime import datetime, timezone
import json

from youtube_audio import AudioDownloadClient
from youtube_audio.interfaces import VideoAudioInfo

from .interfaces import TranscriptionClient, YouTubeTranscript


class YouTubeTranscriptService:
    """Orchestrates:
    1) YouTube -> cached audio + metadata (via youtube_audio)
    2) audio file -> transcript (via TranscriptionClient)
    3) optional per-video transcript caching
    """

    def __init__(
        self,
        audio_client: AudioDownloadClient,
        transcriber: TranscriptionClient,
        *,
        transcript_cache_dir: str | Path = "cache/transcripts",
    ) -> None:
        self._audio = audio_client
        self._tx = transcriber
        self._tcache = Path(transcript_cache_dir).resolve()
        self._tcache.mkdir(parents=True, exist_ok=True)

    def _transcript_path(self, video_id: str) -> Path:
        return (self._tcache / f"{video_id}.json").resolve()

    def _read_cached(self, video_id: str) -> Optional[Dict[str, Any]]:
        p = self._transcript_path(video_id)
        if not p.exists():
            return None
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _write_cached(self, video_id: str, payload: Dict[str, Any]) -> None:
        payload = {**payload, "updated_at": datetime.now(timezone.utc).isoformat()}
        tmp = self._tcache / f"{video_id}.json.tmp"
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        tmp.replace(self._transcript_path(video_id))

    def get_transcript(
        self,
        url: str,
        *,
        force: bool = False,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> YouTubeTranscript:
        info: VideoAudioInfo = self._audio.get_info(url)

        if not force:
            cached = self._read_cached(info.video_id)
            if cached and isinstance(cached.get("transcript"), str):
                return YouTubeTranscript(
                    url=str(cached.get("url") or url),
                    video_id=str(cached.get("video_id") or info.video_id),
                    title=str(cached.get("title") or info.title),
                    description=str(cached.get("description") or info.description),
                    transcript=str(cached.get("transcript") or ""),
                )

        text = self._tx.transcribe(info.audio_path, language=language, prompt=prompt)

        out = YouTubeTranscript(
            url=url,
            video_id=info.video_id,
            title=info.title,
            description=info.description,
            transcript=text,
        )

        self._write_cached(info.video_id, {
            "url": out.url,
            "video_id": out.video_id,
            "title": out.title,
            "description": out.description,
            "transcript": out.transcript,
        })

        return out

    def get_transcript_json(
        self,
        url: str,
        *,
        force: bool = False,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        t = self.get_transcript(url, force=force, language=language, prompt=prompt)
        return {
            "url": t.url,
            "video_id": t.video_id,
            "title": t.title,
            "description": t.description,
            "transcript": t.transcript,
        }
