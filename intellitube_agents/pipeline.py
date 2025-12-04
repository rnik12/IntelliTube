from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents import Runner

from .context import build_context
from .indexer.agent import build_indexer_agent
from .script.agent import build_script_agent
from .schema import IndexerResult, ScriptResult


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _log(stage: str, **fields: object) -> None:
    print(json.dumps({"ts": _ts(), "stage": stage, **fields}, ensure_ascii=False))


def _read_json_file(p: Path) -> dict[str, Any] | None:
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def main() -> None:
    p = argparse.ArgumentParser(description="Indexer agent (cache transcripts) -> Script agent (2 variants)")
    p.add_argument("search_query", help="Search query to find reference videos")
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--topic", required=True, help="New topic to write about")
    p.add_argument("--by-date", action="store_true")
    p.add_argument("--max-duration", type=int, default=60)
    p.add_argument("--transcribe-model", default="whisper-1")
    p.add_argument("--max-knowledge-chars", type=int, default=250_000, help="Cap total transcript chars injected")
    args = p.parse_args()

    _log("start", search_query=args.search_query, limit=args.limit, by_date=args.by_date, max_duration=args.max_duration)

    _log("context.build.begin", transcribe_model=args.transcribe_model)
    ctx = build_context(transcribe_model=args.transcribe_model)
    _log("context.build.end")

    indexer = build_indexer_agent()
    writer = build_script_agent()

    # -------- 1) Indexer agent: search + transcribe/cache --------
    _log("indexer.run.begin")
    indexer_input = (
        f"query: {args.search_query}\n"
        f"limit: {args.limit}\n"
        f"sort_by_date: {bool(args.by_date)}\n"
        f"max_duration_seconds: {args.max_duration}\n"
    )
    idx = Runner.run_sync(indexer, indexer_input, context=ctx, max_turns=10)
    index_result: IndexerResult = idx.final_output
    _log("indexer.run.end", found=index_result.found)

    # -------- 2) Build knowledge list in Python (read cached JSON files) --------
    _log("knowledge.build.begin")
    knowledge: list[dict[str, str]] = []
    total = 0
    used_refs: list[str] = []

    for art in index_result.transcripts:
        tp = Path(art.transcript_path).expanduser().resolve()
        data = _read_json_file(tp)
        if not data:
            continue

        title = str(data.get("title") or "")
        desc = str(data.get("description") or "")
        tx = str(data.get("transcript") or "")

        if not tx.strip():
            continue

        if total + len(tx) > args.max_knowledge_chars:
            break

        knowledge.append({"title": title, "description": desc, "transcript": tx})
        used_refs.append(title or art.video_id)
        total += len(tx)

    _log("knowledge.build.end", items=len(knowledge), total_chars=total)

    # -------- 3) Script agent: inject knowledge directly (no tools) --------
    _log("script.run.begin", topic=args.topic)
    knowledge_json = json.dumps(knowledge, ensure_ascii=False)

    writer_input = (
        f"topic: {args.topic}\n\n"
        f"REFERENCE_VIDEOS_JSON:\n{knowledge_json}\n"
    )

    out = Runner.run_sync(writer, writer_input, context=ctx, max_turns=6)
    script_result: ScriptResult = out.final_output
    _log("script.run.end", variant_count=len(script_result.variants))

    final_payload = {
        "index": index_result.model_dump(),
        "script": script_result.model_dump(),
        "variants": [v.model_dump() for v in script_result.variants],
        "reference_titles_used_in_context": used_refs,
    }

    _log("done")
    print(json.dumps(final_payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
