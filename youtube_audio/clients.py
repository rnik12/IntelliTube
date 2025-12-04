from __future__ import annotations
from typing import Optional, Dict, Any
from pathlib import Path
import yt_dlp

class YtDlpAudioClient:
    """Downloads best available audio (preferring m4a) into cache/audio.
    Skips download if the target file already exists.
    Returns the absolute local path.
    """

    def __init__(
        self,
        cache_dir: Optional[str | Path] = None,
        base_opts: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._cache = Path(cache_dir or "cache/audio").resolve()
        self._cache.mkdir(parents=True, exist_ok=True)
        # Prefer containerized audio to avoid ffmpeg dependency
        default_opts: Dict[str, Any] = {
            "quiet": True,
            "noplaylist": True,
            "paths": {"home": str(self._cache)},
            "outtmpl": {"default": "%(id)s.%(ext)s"},
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "restrictfilenames": True,
        }
        self._opts = {**default_opts, **(base_opts or {})}

    def _probe(self, url: str) -> Dict[str, Any]:
        # Lightweight metadata fetch to compute the cache target deterministically
        with yt_dlp.YoutubeDL({**self._opts, "skip_download": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            if info.get("_type") == "playlist":
                raise ValueError("Playlists are not supported. Provide a single video URL.")
            return info

    def download(self, url: str) -> str:
        info = self._probe(url)
        vid = info.get("id")
        # Prefer final ext if known; fall back to 'm4a' for typical YouTube audio
        ext = info.get("ext") or "m4a"
        target = self._cache / f"{vid}.{ext}"
        if target.exists():
            return str(target)

        # Perform download (no transcoding, to keep dependencies minimal)
        with yt_dlp.YoutubeDL(self._opts) as ydl:
            # download returns a list of paths in recent yt-dlp; but to be robust we recompute after
            ydl.download([url])

        # After download, file could have a different ext if extractor chose another bestaudio
        # Resolve by checking typical possibilities
        candidates = [
            target,
            self._cache / f"{vid}.m4a",
            self._cache / f"{vid}.webm",
            self._cache / f"{vid}.opus",
            self._cache / f"{vid}.mp3",
        ]
        for p in candidates:
            if p.exists():
                return str(p.resolve())

        # Fallback: scan for files matching id.*
        matches = list(self._cache.glob(f"{vid}.*"))
        if matches:
            return str(matches[0].resolve())

        raise RuntimeError("Audio download completed but file was not found in cache.")
