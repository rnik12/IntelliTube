from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Optional


@dataclass(frozen=True)
class VideoAudioInfo:
    """Reusable payload for other modules."""
    video_id: str
    title: str
    description: str
    audio_path: str


class AudioDownloadClient(Protocol):
    """Contract to download (or resolve cached) audio for a YouTube URL.
    Returns absolute local file path to the audio file.
    """
    def download(self, url: str) -> str:
        ...

    def get_info(self, url: str) -> VideoAudioInfo:
        """Returns title, description, and absolute local audio path (downloading if needed)."""
        ...
