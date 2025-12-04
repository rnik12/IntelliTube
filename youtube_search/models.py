from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

@dataclass(frozen=True)
class SearchResult:
    id: str
    title: str
    url: str
    channel: Optional[str] = None
    duration_seconds: Optional[int] = None
    upload_date: Optional[str] = None  # YYYYMMDD if available

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class VideoDetails:
    id: str
    title: str
    url: str
    channel: Optional[str]
    duration_seconds: Optional[int]
    upload_date: Optional[str]
    description: Optional[str]
    view_count: Optional[int]
    like_count: Optional[int]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class SearchError(Exception):
    """Raised when a search operation fails."""

class HydrationError(Exception):
    """Raised when a hydration (detail fetch) operation fails."""