"""
Quick demo:

python -m youtube_search "python tutorials" --limit 5 --by-date --hydrate 2

pip install yt-dlp
(Optional) Install Node for full JS runtime support.
"""

from __future__ import annotations
import argparse
from typing import List

from .clients import YtDlpSearchClient, YtDlpDetailClient
from .formatters import DictFormatter, TableFormatter
from .service import YouTubeSearchService


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube search using yt-dlp (SOLID)")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", type=int, default=5, help="Max number of results")
    parser.add_argument("--by-date", action="store_true", help="Sort by recency")
    parser.add_argument(
        "--hydrate", type=int, default=0, help="Hydrate first N results for full details"
    )
    parser.add_argument(
        "--table", action="store_true", help="Output formatted markdown table instead of dicts"
    )

    args = parser.parse_args()

    search_client = YtDlpSearchClient()
    detail_client = YtDlpDetailClient()
    formatter = TableFormatter() if args.table else DictFormatter()

    service = YouTubeSearchService(
        search_client=search_client,
        detail_client=detail_client,
        formatter=formatter,
    )

    out = service.search(query=args.query, limit=args.limit, sort_by_date=args.by_date)
    results = out["results"]

    # Print primary results
    if isinstance(results, str):  # table
        print(results)
    else:  # list of dicts
        for row in results:
            print(row)

    # Optional hydration of first N ids
    if args.hydrate and isinstance(results, list):
        ids: List[str] = [row.get("id") for row in results if row.get("id")]  # type: ignore
        ids = ids[: args.hydrate]
        hydrated_out = service.search(
            query=args.query,
            limit=args.limit,
            sort_by_date=args.by_date,
            hydrate_ids=ids,
        )
        print("\nHydrated details:")
        for d in hydrated_out["hydrated"] or []:
            print(d)

if __name__ == "__main__":
    main()