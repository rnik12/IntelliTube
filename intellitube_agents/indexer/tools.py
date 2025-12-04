from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

from agents import RunContextWrapper, function_tool

from ..context import IntelliTubeContext
from ..schema import SearchResultRow, TranscriptArtifact


@function_tool
def youtube_search_tool(
    ctx: RunContextWrapper[IntelliTubeContext],
    query: str,
    limit: int = 5,
    sort_by_date: bool = False,
    max_duration_seconds: Optional[int] = 60,
) -> list[SearchResultRow]:
    """Search YouTube and return strict-typed results (no transcript text)."""
    q = (query or "").strip()
    if not q or limit <= 0:
        return []

    if limit > 50:
        raise ValueError("limit too large; please use <= 50")

    mds = None
    if max_duration_seconds is not None and max_duration_seconds > 0:
        mds = int(max_duration_seconds)

    out = ctx.context.search_service.search(
        query=q,
        limit=int(limit),
        sort_by_date=bool(sort_by_date),
        max_duration_seconds=mds,
    )

    results = out.get("results", [])
    if not isinstance(results, list):
        raise TypeError("youtube_search_tool expected list results from DictFormatter.")

    return [SearchResultRow.model_validate(r) for r in results]


@function_tool
async def youtube_transcribe_cache_tool(
    ctx: RunContextWrapper[IntelliTubeContext],
    urls: list[str],
    force: bool = False,
    language: Optional[str] = None,
    prompt: Optional[str] = None,
    concurrency: int = 3,
) -> list[TranscriptArtifact]:
    """Ensure cache/transcripts/<video_id>.json exists for each URL.

    Returns ONLY artifact references (path + small stats), NOT transcripts.
    """
    cleaned = [u.strip() for u in (urls or []) if u and u.strip()]
    if not cleaned:
        return []

    sem = asyncio.Semaphore(max(1, min(int(concurrency), 10)))

    async def one(u: str) -> TranscriptArtifact:
        async with sem:
            payload = await asyncio.to_thread(
                ctx.context.transcript_service.get_transcript_json,
                u,
                force=bool(force),
                language=language,
                prompt=prompt,
            )

            video_id = str(payload.get("video_id") or "")
            if not video_id:
                raise RuntimeError(f"Missing video_id for url={u}")

            transcript_path = (ctx.context.transcript_cache_dir / f"{video_id}.json").resolve()

            updated_at: Optional[str] = None
            tlen = 0

            # Read cached JSON to extract stats WITHOUT returning transcript text
            try:
                with transcript_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                updated_at = data.get("updated_at")
                tx = data.get("transcript")
                if isinstance(tx, str):
                    tlen = len(tx)
            except Exception:
                pass

            return TranscriptArtifact(
                video_id=video_id,
                url=str(payload.get("url") or u),
                transcript_path=str(transcript_path),
            )

    artifacts = await asyncio.gather(*[one(u) for u in cleaned])
    return list(artifacts)
