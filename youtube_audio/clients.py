from __future__ import annotations

from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timezone
import json

import yt_dlp

from .interfaces import VideoAudioInfo


class YtDlpAudioClient:
    """Downloads best available audio (preferring m4a) into cache/audio.
    Skips download if the target file already exists.
    Stores metadata per video in: <cache>/<id>.json
    """

    def __init__(
        self,
        cache_dir: Optional[str | Path] = None,
        base_opts: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._cache = Path(cache_dir or "cache/audio").resolve()
        self._cache.mkdir(parents=True, exist_ok=True)

        default_opts: Dict[str, Any] = {
            "quiet": True,
            "noplaylist": True,
            "paths": {"home": str(self._cache)},
            "outtmpl": {"default": "%(id)s.%(ext)s"},
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "restrictfilenames": True,
            "extractor_args": {
                "youtube": {
                    # keep it simple:
                    "player_client": ["default"],
                    # (optional but often helps with the SABR “missing url” spam)
                    # "player_client": ["default", "-web", "-web_safari"],
                }
            },
        }
        self._opts = {**default_opts, **(base_opts or {})}

    def _probe(self, url: str) -> Dict[str, Any]:
        with yt_dlp.YoutubeDL({**self._opts, "skip_download": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            if info.get("_type") == "playlist":
                raise ValueError(
                    "Playlists are not supported. Provide a single video URL."
                )
            return info

    def _meta_path(self, video_id: str) -> Path:
        return (self._cache / f"{video_id}.json").resolve()

    def _write_meta(
        self,
        video_id: str,
        url: str,
        title: str,
        description: str,
        audio_path: str,
    ) -> None:
        payload = {
            "video_id": video_id,
            "url": url,
            "title": title,
            "description": description,
            "audio_path": audio_path,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        tmp = self._cache / f"{video_id}.json.tmp"
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        tmp.replace(self._meta_path(video_id))

    def _read_meta(self, video_id: str) -> Optional[Dict[str, Any]]:
        p = self._meta_path(video_id)
        if not p.exists():
            return None
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _resolve_existing_audio(self, video_id: str) -> Optional[Path]:
        # 1) Prefer per-video json pointer if valid
        meta = self._read_meta(video_id)
        if isinstance(meta, dict):
            ap = meta.get("audio_path")
            if isinstance(ap, str) and ap:
                candidate = Path(ap)
                if candidate.is_absolute() and candidate.exists():
                    return candidate.resolve()
                candidate2 = (self._cache / ap).resolve()
                if candidate2.exists():
                    return candidate2

        # 2) Otherwise, scan cache for id.*
        matches = sorted(self._cache.glob(f"{video_id}.*"))
        for m in matches:
            if m.is_file() and m.suffix.lower() != ".json":
                return m.resolve()
        return None

    def _download_and_resolve(self, url: str, info: Dict[str, Any]) -> Path:
        video_id = info.get("id")
        if not video_id:
            raise RuntimeError("yt-dlp did not return a video id.")

        existing = self._resolve_existing_audio(video_id)
        if existing:
            return existing

        # Download (no transcoding)
        with yt_dlp.YoutubeDL(self._opts) as ydl:
            ydl.download([url])

        existing = self._resolve_existing_audio(video_id)
        if existing:
            return existing

        raise RuntimeError("Audio download completed but file was not found in cache.")

    # ---- Public API ----
    def get_info(self, url: str) -> VideoAudioInfo:
        info = self._probe(url)
        video_id = info.get("id")
        if not video_id:
            raise RuntimeError("yt-dlp did not return a video id.")

        title = (info.get("title") or "").strip()
        description = (info.get("description") or "").strip()

        audio_path = self._download_and_resolve(url, info).resolve()

        # Write <id>.json beside the audio
        self._write_meta(
            video_id=video_id,
            url=url,
            title=title,
            description=description,
            audio_path=str(audio_path),
        )

        return VideoAudioInfo(
            video_id=video_id,
            title=title,
            description=description,
            audio_path=str(audio_path),
        )

    def download(self, url: str) -> str:
        return self.get_info(url).audio_path
