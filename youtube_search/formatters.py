from typing import List, Dict, Any
from .interfaces import ResultFormatter
from .models import SearchResult

class DictFormatter(ResultFormatter):
    """Returns a plain list[dict] for easy JSON serialization or DataFrame creation."""

    def format_results(self, results: List[SearchResult]) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in results]

class TableFormatter(ResultFormatter):
    """Returns a compact, human-friendly markdown table string."""

    def format_results(self, results: List[SearchResult]) -> str:
        if not results:
            return "No results."
        headers = ["Title", "URL", "Channel", "Duration(s)", "Upload Date"]
        lines = [" | ".join(headers), " | ".join("---" for _ in headers)]
        for r in results:
            lines.append(
                " | ".join([
                    (r.title or "").replace("|", "/"),
                    r.url or "",
                    (r.channel or "").replace("|", "/"),
                    str(r.duration_seconds or ""),
                    r.upload_date or "",
                ])
            )
        return "\n".join(lines)