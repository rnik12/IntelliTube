from typing import Protocol

class AudioDownloadClient(Protocol):
    """Contract to download (or resolve cached) audio for a YouTube URL.
    Returns absolute local file path to the audio file.
    """
    def download(self, url: str) -> str:
        ...
