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
    video_id: str
    url: str
    title: str
    description: str
    transcript_path: str
    updated_at: Optional[str] = None
    transcript_chars: int = 0


class ManifestWriteOutput(BaseModel):
    manifest_path: str
    video_count: int


# ---------- Manifest schema ----------

class ManifestEntry(BaseModel):
    rank: int
    video_id: str
    url: str

    channel: Optional[str] = None
    duration_seconds: Optional[int] = None
    upload_date: Optional[str] = None

    transcript_path: str
    transcript_chars: int = 0
    transcript_updated_at: Optional[str] = None

    title: str = ""
    description: str = ""


class ManifestFile(BaseModel):
    schema_version: str = "intellitube.manifest.v1"
    created_at: str
    search_query: str
    limit: int
    model: str
    entries: List[ManifestEntry]


class ManifestPointer(BaseModel):
    manifest_path: str
    video_count: int


# ---------- Script agent output ----------

class KnowledgeItem(BaseModel):
    title: str
    description: str
    transcript: str


class ScriptOutput(BaseModel):
    topic: str = Field(..., description="Requested topic for the new script.")
    style_notes: List[str] = Field(default_factory=list, description="Style traits learned from references.")
    references: List[str] = Field(default_factory=list, description="Reference titles used.")
    transcript: str = Field(..., description="Newly generated transcript/script.")
