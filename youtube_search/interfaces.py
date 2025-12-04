from typing import List, Iterable, Protocol, Any, runtime_checkable
from .models import SearchResult, VideoDetails

@runtime_checkable
class SearchClient(Protocol):
    """Minimal contract required to search videos."""
    def search(self, query: str, limit: int, sort_by_date: bool = False) -> List[SearchResult]:
        ...

@runtime_checkable
class DetailClient(Protocol):
    """Optional contract for fetching full details of one or more videos."""
    def get_details(self, video_ids: Iterable[str]) -> List[VideoDetails]:
        ...

@runtime_checkable
class ResultFormatter(Protocol):
    """Formatter strategy for presenting results (dicts, markdown table, JSON, etc.)."""
    def format_results(self, results: List[SearchResult]) -> Any:
        ...