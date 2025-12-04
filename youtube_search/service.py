from typing import Optional, Iterable, Dict, Any, List

from .interfaces import SearchClient, DetailClient, ResultFormatter
from .models import HydrationError, SearchResult

class YouTubeSearchService:
    """
    High-level façade that composes:
      - a SearchClient (required)
      - an optional DetailClient (for hydration)
      - a ResultFormatter (output strategy)
    """

    def __init__(
        self,
        search_client: SearchClient,
        formatter: ResultFormatter,
        detail_client: Optional[DetailClient] = None,
    ) -> None:
        self._search_client = search_client
        self._detail_client = detail_client
        self._formatter = formatter

    def search(
        self,
        query: str,
        limit: int = 5,
        sort_by_date: bool = False,
        hydrate_ids: Optional[Iterable[str]] = None,
        max_duration_seconds: Optional[int] = 60,  # <= add this
    ) -> Dict[str, Any]:
        """
        Returns a structured payload:
        {
            "results": <formatted results>,
            "hydrated": [VideoDetails as dicts] or None
        }
        """

        if limit <= 0:
            return {"results": self._formatter.format_results([]), "hydrated": None}

        # Overfetch to compensate for filtering (cap to avoid huge requests)
        expanded_limit = limit
        if max_duration_seconds is not None:
            expanded_limit = min(max(limit * 10, limit), 200)

        results: List[SearchResult] = self._search_client.search(
            query=query,
            limit=expanded_limit,
            sort_by_date=sort_by_date,
        )

        # Apply duration filter: keep only items with known duration <= max
        if max_duration_seconds is not None:
            results = [
                r
                for r in results
                if r.duration_seconds is not None and r.duration_seconds <= max_duration_seconds
            ]

        # Enforce final limit after filtering
        results = results[:limit]

        formatted = self._formatter.format_results(results)
        payload: Dict[str, Any] = {"results": formatted, "hydrated": None}

        if hydrate_ids:
            if not self._detail_client:
                raise HydrationError("Hydration requested but no DetailClient configured.")
            details = self._detail_client.get_details(hydrate_ids)
            payload["hydrated"] = [d.to_dict() for d in details]

        return payload
