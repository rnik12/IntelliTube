from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from agents import RunContextWrapper, function_tool

from ..context import IntelliTubeContext
from ..schema import (
    SearchResultRow,
    TranscriptArtifact,
    ManifestFile,
    ManifestEntry,
    ManifestWriteOutput,
)


@function_tool
def youtube_search_tool(
    ctx: RunContextWrapper[IntelliTubeContext],
    query: str,
    limit: int = 5,
    sort_by_date: bool = False,
    max_duration_seconds: Optional[int] = 60,
) -> list[SearchResultRow]:
    """Search YouTube and return strict-typed results."""
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

    typed: list[SearchResultRow] = []
    for r in results:
        # DictFormatter returns dict; validate into a strict Pydantic model
        typed.append(SearchResultRow.model_validate(r))
    return typed


@function_tool
async def youtube_transcribe_cache_tool(
    ctx: RunContextWrapper[IntelliTubeContext],
    urls: list[str],
    force: bool = False,
    language: Optional[str] = None,
    prompt: Optional[str] = None,
    concurrency: int = 3,
) -> list[TranscriptArtifact]:
    """Transcribe URLs and ensure cache/transcripts/<video_id>.json exists.
    Returns only artifact metadata and transcript path (no transcript text).
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

            # Read cached JSON to extract stats (not transcript output)
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
                title=str(payload.get("title") or ""),
                description=str(payload.get("description") or ""),
                transcript_path=str(transcript_path),
                updated_at=updated_at,
                transcript_chars=tlen,
            )

    artifacts = await asyncio.gather(*[one(u) for u in cleaned])
    return list(artifacts)


@function_tool
def write_manifest_tool(
    ctx: RunContextWrapper[IntelliTubeContext],
    search_query: str,
    limit: int,
    model: str,
    search_results: list[SearchResultRow],
    transcript_artifacts: list[TranscriptArtifact],
) -> ManifestWriteOutput:
    """Write a durable manifest JSON referencing cached transcript JSON files."""
    tmap = {a.video_id: a for a in (transcript_artifacts or [])}

    entries: list[ManifestEntry] = []
    rank = 1

    for r in (search_results or []):
        ta = tmap.get(r.id)
        if not ta:
            continue  # skip if transcription failed / missing

        entries.append(
            ManifestEntry(
                rank=rank,
                video_id=r.id,
                url=r.url or ta.url,
                channel=r.channel,
                duration_seconds=r.duration_seconds,
                upload_date=r.upload_date,
                transcript_path=ta.transcript_path,
                transcript_chars=ta.transcript_chars,
                transcript_updated_at=ta.updated_at,
                title=ta.title or r.title,
                description=ta.description or "",
            )
        )
        rank += 1

    created_at = datetime.now(timezone.utc).isoformat()
    manifest = ManifestFile(
        created_at=created_at,
        search_query=str(search_query),
        limit=int(limit),
        model=str(model),
        entries=entries,
    )

    safe = "".join(ch if ch.isalnum() else "-" for ch in (search_query or "query"))[:60].strip("-")
    fname = f"{created_at.replace(':','').replace('.','')}_{safe}_{len(entries)}.json"
    manifest_path = (ctx.context.manifest_dir / fname).resolve()

    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest.model_dump(), f, ensure_ascii=False, indent=2, sort_keys=True)

    return ManifestWriteOutput(manifest_path=str(manifest_path), video_count=len(entries))
