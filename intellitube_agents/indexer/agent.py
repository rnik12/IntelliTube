from __future__ import annotations

from agents import Agent

from ..context import IntelliTubeContext
from ..schema import IndexerResult
from .tools import youtube_search_tool, youtube_transcribe_cache_tool

INDEXER_INSTRUCTIONS = """
You are IntelliTubeIndexer.

Goal: Ensure transcripts are downloaded and cached (cache/transcripts/<video_id>.json).

Steps:
1) Call youtube_search_tool(query, limit, sort_by_date, max_duration_seconds).
2) Extract URLs from results in order.
3) Call youtube_transcribe_cache_tool(urls=[...]) exactly once.
4) Return IndexerResult with:
   - search_query
   - requested_limit
   - found
   - transcripts: ordered list of TranscriptArtifact (with transcript_path etc.)

Important:
- NEVER return transcript text.
""".strip()


def build_indexer_agent() -> Agent[IntelliTubeContext]:
    return Agent[IntelliTubeContext](
        name="IntelliTubeIndexer",
        model="gpt-4o-mini",
        instructions=INDEXER_INSTRUCTIONS,
        tools=[youtube_search_tool, youtube_transcribe_cache_tool],
        output_type=IndexerResult,
    )
