from .interfaces import AudioDownloadClient

class YouTubeAudioService:
    """Thin façade orchestrating audio downloads (or cache hits)."""

    def __init__(self, client: AudioDownloadClient) -> None:
        self._client = client

    def download_audio(self, url: str) -> str:
        """Returns absolute local path to the cached or newly downloaded audio."""
        return self._client.download(url)
