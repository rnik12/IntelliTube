from __future__ import annotations
from .interfaces import AudioDownloadClient, VideoAudioInfo


class YouTubeAudioService:
    """Thin façade orchestrating audio downloads (or cache hits)."""

    def __init__(self, client: AudioDownloadClient) -> None:
        self._client = client

    def download_audio(self, url: str) -> str:
        """Returns absolute local path to the cached or newly downloaded audio."""
        # keep behavior, but we can reuse get_info() to avoid duplication
        return self._client.get_info(url).audio_path

    def get_audio_info(self, url: str) -> VideoAudioInfo:
        """Returns title, description, and absolute local audio path (downloading if needed)."""
        return self._client.get_info(url)
