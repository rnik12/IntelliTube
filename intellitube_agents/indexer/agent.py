from __future__ import annotations

from agents import Agent

from ..context import IntelliTubeContext
from ..schema import ManifestPointer, ManifestWriteOutput
from .tools import youtube_search_tool, youtube_transcribe_cache_tool, write_manifest_tool


INDEXER_INSTRUCTIONS = """
You are IntelliTubeIndexer.

Goal: Create a manifest file referencing cached transcript JSON files.

Must-follow steps:
1) Call youtube_search_tool(query, limit, sort_by_date, max_duration_seconds).
2) Extract URLs from results in order.
3) Call youtube_transcribe_cache_tool(urls=[...]) exactly once.
4) Call write_manifest_tool(search_query, limit, model, search_results, transcript_artifacts).
5) Return ONLY {manifest_path, video_count} as ManifestPointer.

Never output transcript text.
""".strip()


def build_indexer_agent() -> Agent[IntelliTubeContext]:
    return Agent[IntelliTubeContext](
        name="IntelliTubeIndexer",
        model="gpt-4o-mini",
        instructions=INDEXER_INSTRUCTIONS,
        tools=[youtube_search_tool, youtube_transcribe_cache_tool, write_manifest_tool],
        output_type=ManifestPointer,
    )
