from __future__ import annotations

import json
from pathlib import Path

from agents import RunContextWrapper, function_tool

from ..context import IntelliTubeContext
from ..schema import ManifestFile, KnowledgeItem


@function_tool
def load_knowledge_from_manifest_tool(
    ctx: RunContextWrapper[IntelliTubeContext],
    manifest_path: str,
    max_total_chars: int = 1_500_000,
) -> list[KnowledgeItem]:
    """Load ALL transcripts referenced by the manifest into strict KnowledgeItems.

    WARNING: This becomes model-visible. Keep it bounded via:
    - indexer limit + duration filter
    - max_total_chars
    """
    mp = Path(manifest_path).expanduser().resolve()
    if not mp.exists():
        raise FileNotFoundError(f"Manifest not found: {mp}")

    with mp.open("r", encoding="utf-8") as f:
        manifest = ManifestFile.model_validate(json.load(f))

    knowledge: list[KnowledgeItem] = []
    total = 0

    for e in manifest.entries:
        tp = Path(e.transcript_path).expanduser().resolve()
        if not tp.exists():
            continue

        with tp.open("r", encoding="utf-8") as f:
            data = json.load(f)

        title = str(data.get("title") or e.title or "")
        desc = str(data.get("description") or e.description or "")
        tx = str(data.get("transcript") or "")

        if total + len(tx) > max_total_chars:
            break

        knowledge.append(KnowledgeItem(title=title,description=desc,transcript=tx))
        total += len(tx)

    return knowledge
