from typing import Optional, Iterable, Dict, Any

from .interfaces import SearchClient, DetailClient, ResultFormatter
from .models import HydrationError

class YouTubeSearchService:
    """
    High-level façade that composes:
      - a SearchClient (required)
      - an optional DetailClient (for hydration)
      - a ResultFormatter (output strategy)

    Adheres to SOLID:
      - SRP: Orchestrates search/hydration/formatting only.
      - OCP: Swap clients/formatters without modifying this class.
      - LSP: Accepts any implementation of the Protocols.
      - ISP: Separate interfaces for searching vs. hydration vs. formatting.
      - DIP: Depends on abstractions (Protocols), not concretions.
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
    ) -> Dict[str, Any]:
        """
        Returns a structured payload:
        {
            "results": <formatted results>,
            "hydrated": [VideoDetails as dicts] or None
        }
        """
        results = self._search_client.search(query=query, limit=limit, sort_by_date=sort_by_date)
        formatted = self._formatter.format_results(results)

        payload: Dict[str, Any] = {"results": formatted, "hydrated": None}

        if hydrate_ids:
            if not self._detail_client:
                raise HydrationError("Hydration requested but no DetailClient configured.")
            details = self._detail_client.get_details(hydrate_ids)
            payload["hydrated"] = [d.to_dict() for d in details]

        return payload