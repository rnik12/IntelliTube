from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, List


# ---------- Tool I/O models (strict schemas) ----------

class SearchResultRow(BaseModel):
    id: str
    title: str
    url: str
    channel: Optional[str] = None
    duration_seconds: Optional[int] = None
    upload_date: Optional[str] = None  # YYYYMMDD if available


class TranscriptArtifact(BaseModel):
    # IMPORTANT: No transcript text here. Only references/metadata.
    video_id: str
    url: str
    transcript_path: str


class IndexerResult(BaseModel):
    search_query: str
    requested_limit: int
    found: int
    transcripts: List[TranscriptArtifact]  # ordered to match search results


# ---------- Script agent: supply knowledge via Python (not tools) ----------

class VideoVariant(BaseModel):
    title: str = Field(..., description="Short, clickable title for the YouTube Short.")
    description: str = Field(..., description="Description aligned with transcript.")
    transcript: str = Field(..., description="Spoken script intended for <60s delivery.")


class ScriptResult(BaseModel):
    topic: str
    style_notes: List[str] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)
    variants: List[VideoVariant] = Field(..., min_length=2, max_length=2)
