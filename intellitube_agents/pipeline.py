from __future__ import annotations

import argparse
import json

from agents import Runner

from .context import build_context
from .indexer.agent import build_indexer_agent
from .script.agent import build_script_agent


def main() -> None:
    p = argparse.ArgumentParser(description="Indexer -> Manifest -> Script Writer pipeline (Agents SDK)")
    p.add_argument("search_query", help="Search query to find reference videos")
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--topic", required=True, help="New topic to write about")
    p.add_argument("--by-date", action="store_true")
    p.add_argument("--max-duration", type=int, default=60)
    p.add_argument("--transcribe-model", default="whisper-1")
    args = p.parse_args()

    ctx = build_context(transcribe_model=args.transcribe_model)
    indexer = build_indexer_agent()
    writer = build_script_agent()

    # Step 1: index -> manifest
    indexer_input = (
        f"query: {args.search_query}\n"
        f"limit: {args.limit}\n"
        f"sort_by_date: {bool(args.by_date)}\n"
        f"max_duration_seconds: {args.max_duration}\n"
    )
    idx = Runner.run_sync(indexer, indexer_input, context=ctx, max_turns=12)
    manifest_ptr = idx.final_output  # ManifestPointer

    # Step 2: manifest + topic -> new transcript
    writer_input = (
        f"manifest_path: {manifest_ptr.manifest_path}\n"
        f"topic: {args.topic}\n"
    )
    out = Runner.run_sync(writer, writer_input, context=ctx, max_turns=10)
    script = out.final_output  # ScriptOutput

    print(json.dumps(
        {"manifest": manifest_ptr.model_dump(), "script": script.model_dump()},
        ensure_ascii=False,
        indent=2
    ))


if __name__ == "__main__":
    main()
