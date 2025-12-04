from __future__ import annotations

from agents import Agent

from ..context import IntelliTubeContext
from ..schema import ScriptOutput
from .tools import load_knowledge_from_manifest_tool


SCRIPT_INSTRUCTIONS = """
You are IntelliTubeScriptWriter.

Task:
Given a NEW topic, create TWO variant ideas for a YouTube Short (< 60 seconds each).
Each variant must include: title, description, transcript.

Reference use:
You MUST call load_knowledge_from_manifest_tool(manifest_path) to obtain a list of:
{title, description, transcript}.
Use these as style/tone/structure reference (hooks, pacing, formatting, CTA style).

Constraints:
- Each transcript should fit a <60s spoken delivery.
- Keep description concise and aligned to the transcript.

Output:
Return ONLY a JSON array with exactly 2 objects.
Each object MUST contain exactly these keys:
- "title" (string)
- "description" (string)
- "transcript" (string)

Inputs:
- manifest_path
- topic
""".strip()


def build_script_agent() -> Agent[IntelliTubeContext]:
    return Agent[IntelliTubeContext](
        name="IntelliTubeScriptWriter",
        model="gpt-5-mini-2025-08-07",
        instructions=SCRIPT_INSTRUCTIONS,
        tools=[load_knowledge_from_manifest_tool],
        output_type=ScriptOutput,
    )
