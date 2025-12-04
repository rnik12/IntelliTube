from dataclasses import dataclass
from typing import Protocol, Optional


@dataclass(frozen=True)
class YouTubeTranscript:
    url: str
    video_id: str
    title: str
    description: str
    transcript: str


class TranscriptionClient(Protocol):
    """Contract for converting a local audio file into text."""

    def transcribe(
        self,
        audio_path: str,
        *,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> str:
        ...
