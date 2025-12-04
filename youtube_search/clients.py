from typing import Optional, Dict, Any, List, Iterable
import yt_dlp

from .models import SearchResult, VideoDetails, SearchError, HydrationError
from .interfaces import SearchClient, DetailClient

class YtDlpSearchClient(SearchClient):
    """
    Performs a 'flat' search with yt-dlp (no formats), avoiding JS runtime warnings.
    Returns basic, robust fields sufficient for listings.
    """

    def __init__(self, base_opts: Optional[Dict[str, Any]] = None) -> None:
        default_opts = {
            "quiet": True,
            "skip_download": True,
            "noplaylist": True,
            "extract_flat": "in_playlist",
            "default_search": "ytsearch",
        }
        self._opts = {**default_opts, **(base_opts or {})}

    def search(self, query: str, limit: int, sort_by_date: bool = False) -> List[SearchResult]:
        if limit <= 0:
            return []
        prefix = "ytsearchdate" if sort_by_date else "ytsearch"
        search_url = f"{prefix}{limit}:{query}"
        try:
            with yt_dlp.YoutubeDL(self._opts) as ydl:
                info = ydl.extract_info(search_url, download=False)
        except Exception as e:
            raise SearchError(f"Search failed: {e}") from e

        entries = info.get("entries", []) if isinstance(info, dict) else []
        results: List[SearchResult] = []

        for e in entries:
            vid = e.get("id")
            title = e.get("title")
            if not (vid and title):
                continue
            url = f"https://youtu.be/{vid}"
            channel = (e.get("uploader") or e.get("channel"))
            duration = e.get("duration")
            upload_date = e.get("upload_date")

            results.append(
                SearchResult(
                    id=vid,
                    title=title,
                    url=url,
                    channel=channel,
                    duration_seconds=duration,
                    upload_date=upload_date,
                )
            )
        return results

class YtDlpDetailClient(DetailClient):
    """
    Fetches detailed metadata for videos (per-id hydration).
    Uses extractor args that avoid requiring a JS runtime.
    """

    def __init__(self, base_opts: Optional[Dict[str, Any]] = None) -> None:
        default_opts = {
            "quiet": True,
            "skip_download": True,
            # Avoid JS runtime requirement and SABR-only formats
            "extractor_args": {"youtube": {"player_client": ["default"]}},
        }
        self._opts = {**default_opts, **(base_opts or {})}

    def get_details(self, video_ids: Iterable[str]) -> List[VideoDetails]:
        hydrated: List[VideoDetails] = []
        try:
            with yt_dlp.YoutubeDL(self._opts) as ydl:
                for vid in video_ids:
                    info = ydl.extract_info(vid, download=False)
                    hydrated.append(
                        VideoDetails(
                            id=info.get("id") or vid,
                            title=info.get("title"),
                            url=info.get("webpage_url") or f"https://youtu.be/{vid}",
                            channel=(info.get("uploader") or info.get("channel")),
                            duration_seconds=info.get("duration"),
                            upload_date=info.get("upload_date"),
                            description=info.get("description"),
                            view_count=info.get("view_count"),
                            like_count=info.get("like_count"),
                        )
                    )
        except Exception as e:
            raise HydrationError(f"Detail fetch failed: {e}") from e

        return hydrated
