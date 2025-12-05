from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import gradio as gr
from agents import Runner

from intellitube_agents.context import build_context, IntelliTubeContext
from intellitube_agents.indexer.agent import build_indexer_agent
from intellitube_agents.schema import IndexerResult, ScriptResult, VideoVariant
from intellitube_agents.script.agent import build_script_agent
from intellitube_agents.tts import TTSConfig, synthesize_tts_to_file


CSS = """
<style>
:root { --radius: 16px; }
#app-wrap { max-width: 1200px; margin: 0 auto; }
.card {
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: var(--radius);
  padding: 16px;
  background: rgba(255,255,255,0.03);
}
.refs {
  border-radius: var(--radius);
  padding: 14px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.03);
  max-height: 520px;
  overflow: auto;
}
.small-note { opacity: 0.85; font-size: 0.92rem; }
.header {
  display:flex; align-items:flex-end; gap:12px;
  justify-content:space-between; margin-bottom: 10px;
}
.title { font-size: 26px; font-weight: 800; letter-spacing: 0.2px; }
.sub { opacity: 0.85; font-size: 0.95rem; }
</style>
"""


def _read_json_file(p: Path) -> Dict[str, Any] | None:
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _fmt_duration(seconds: Optional[int]) -> str:
    if not seconds or seconds <= 0:
        return ""
    m = seconds // 60
    s = seconds % 60
    return f"{m}:{s:02d}"


def _build_refs_markdown(refs: List[Dict[str, Any]], title: str = "Reference videos (from your YouTube search)") -> str:
    if not refs:
        return f"### {title}\n\n_No references found yet._"
    lines = [f"### {title}", ""]
    for r in refs:
        t = (r.get("title") or "").strip() or "Untitled"
        url = (r.get("url") or "").strip()
        ch = (r.get("channel") or "").strip()
        dur = _fmt_duration(r.get("duration_seconds"))
        meta = " · ".join([x for x in [ch, dur] if x])
        if url:
            lines.append(f"- [{t}]({url})" + (f"  \n  <small>{meta}</small>" if meta else ""))
        else:
            lines.append(f"- {t}" + (f"  \n  <small>{meta}</small>" if meta else ""))
    return "\n".join(lines)


def _run_intellitube(
    search_query: str,
    topic: str,
    limit: int,
    sort_by_date: bool,
    max_duration_seconds: int,
    transcribe_model: str,
    max_knowledge_chars: int,
    tts_speed: float,
    tts_model: str,
    tts_voice: str,
):
    q = (search_query or "").strip()
    tp = (topic or "").strip()
    if not q:
        raise gr.Error("Please enter a YouTube search query.")
    if not tp:
        raise gr.Error("Please enter a topic.")

    limit = int(max(1, min(int(limit), 50)))
    max_duration_seconds = int(max(5, int(max_duration_seconds)))
    max_knowledge_chars = int(max(10_000, int(max_knowledge_chars)))

    # --- context + agents ---
    ctx: IntelliTubeContext = build_context(transcribe_model=transcribe_model)
    indexer = build_indexer_agent()
    writer = build_script_agent()

    # --- 1) Indexer: search + cache transcripts ---
    indexer_input = (
        f"query: {q}\n"
        f"limit: {limit}\n"
        f"sort_by_date: {bool(sort_by_date)}\n"
        f"max_duration_seconds: {max_duration_seconds}\n"
    )
    idx_out = Runner.run_sync(indexer, indexer_input, context=ctx, max_turns=10)
    index_result: IndexerResult = idx_out.final_output

    # --- 2) Build knowledge & refs (read cached JSON files) ---
    knowledge: List[Dict[str, str]] = []
    used_refs: List[Dict[str, Any]] = []
    total = 0

    for art in index_result.transcripts:
        tp_json = Path(art.transcript_path).expanduser().resolve()
        data = _read_json_file(tp_json)
        if not data:
            continue

        title = str(data.get("title") or "")
        desc = str(data.get("description") or "")
        tx = str(data.get("transcript") or "")

        used_refs.append(
            {
                "title": title,
                "url": str(data.get("url") or art.url or ""),
                "channel": str(data.get("channel") or ""),
                "duration_seconds": data.get("duration_seconds"),
            }
        )

        if not tx.strip():
            continue

        if total + len(tx) > max_knowledge_chars:
            break

        knowledge.append({"title": title, "description": desc, "transcript": tx})
        total += len(tx)

    # --- 3) Script writer: 2 variants ---
    knowledge_json = json.dumps(knowledge, ensure_ascii=False)
    writer_input = f"topic: {tp}\n\nREFERENCE_VIDEOS_JSON:\n{knowledge_json}\n"

    out = Runner.run_sync(writer, writer_input, context=ctx, max_turns=6)
    script_result: ScriptResult = out.final_output

    v1: VideoVariant = script_result.variants[0]
    v2: VideoVariant = script_result.variants[1]

    # --- 4) TTS ---
    tts_cfg = TTSConfig(model=tts_model, voice=tts_voice, speed=float(tts_speed))
    a1 = synthesize_tts_to_file(v1.transcript, cfg=tts_cfg)
    a2 = synthesize_tts_to_file(v2.transcript, cfg=tts_cfg)

    refs_md = _build_refs_markdown(used_refs)

    return (
        v1.title,
        v1.description,
        str(a1),
        v2.title,
        v2.description,
        str(a2),
        refs_md,
    )


def build_ui() -> gr.Blocks:
    # NOTE: ultra-compatible: don't pass theme= or css= to Blocks for older Gradio
    with gr.Blocks() as demo:
        gr.HTML(CSS)
        gr.HTML(
            """
            <div id="app-wrap">
              <div class="header">
                <div>
                  <div class="title">IntelliTube</div>
                  <div class="sub">Search YouTube → cache transcripts → write 2 short scripts → generate TTS audio</div>
                </div>
              </div>
            </div>
            """
        )

        with gr.Row():
            # LEFT: Inputs
            with gr.Column(scale=7):
                with gr.Group():
                    gr.HTML('<div class="card">')
                    search_query = gr.Textbox(
                        label="YouTube search query",
                        placeholder='e.g. "learn python"',
                        lines=1,
                    )
                    topic = gr.Textbox(
                        label="New Short topic",
                        placeholder='e.g. "SQL can be integrated in Python using SQLAlchemy"',
                        lines=2,
                    )

                    with gr.Accordion("Advanced search/transcribe settings", open=False):
                        limit = gr.Slider(1, 50, value=10, step=1, label="Search limit")
                        max_duration = gr.Slider(10, 300, value=60, step=5, label="Max duration (seconds)")
                        sort_by_date = gr.Checkbox(value=False, label="Sort by date")
                        transcribe_model = gr.Textbox(value="whisper-1", label="Transcribe model")
                        max_knowledge_chars = gr.Slider(
                            50_000, 1_500_000, value=250_000, step=10_000, label="Max total transcript chars injected"
                        )

                    with gr.Accordion("Audio (TTS) settings", open=True):
                        tts_speed = gr.Slider(0.75, 1.5, value=1.1, step=0.05, label="Playback speed")
                        tts_voice = gr.Dropdown(
                            choices=["alloy", "ash", "ballad", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer", "verse"],
                            value="alloy",
                            label="Voice",
                        )
                        tts_model = gr.Dropdown(
                            choices=["tts-1-hd", "tts-1", "gpt-4o-mini-tts"],
                            value="tts-1-hd",
                            label="TTS model",
                        )
                        gr.Markdown(
                            "<div class='small-note'>Tip: install <b>ffmpeg</b> if you want exact speed control (auto-used if present).</div>"
                        )

                    run_btn = gr.Button("Generate (2 variants + audio)", variant="primary")
                    gr.HTML("</div>")  # end .card

            # RIGHT: References sidebar
            with gr.Column(scale=5):
                gr.HTML('<div class="refs">')
                refs_md = gr.Markdown("### Reference videos (from your YouTube search)\n\n_Run a generation to populate this list._")
                gr.HTML("</div>")

        gr.Markdown("")

        # Outputs (two rows)
        gr.HTML('<div id="app-wrap"><div class="card">')
        gr.Markdown("### Outputs")

        with gr.Row():
            with gr.Column(scale=7):
                v1_title = gr.Textbox(label="Variant 1 — Title", lines=1)
                v1_desc = gr.Textbox(label="Variant 1 — Description", lines=3)
            with gr.Column(scale=5):
                v1_audio = gr.Audio(label="Variant 1 — Audio", type="filepath")

        gr.Markdown("---")

        with gr.Row():
            with gr.Column(scale=7):
                v2_title = gr.Textbox(label="Variant 2 — Title", lines=1)
                v2_desc = gr.Textbox(label="Variant 2 — Description", lines=3)
            with gr.Column(scale=5):
                v2_audio = gr.Audio(label="Variant 2 — Audio", type="filepath")

        gr.HTML("</div></div>")  # end .card & #app-wrap

        run_btn.click(
            fn=_run_intellitube,
            inputs=[
                search_query,
                topic,
                limit,
                sort_by_date,
                max_duration,
                transcribe_model,
                max_knowledge_chars,
                tts_speed,
                tts_model,
                tts_voice,
            ],
            outputs=[v1_title, v1_desc, v1_audio, v2_title, v2_desc, v2_audio, refs_md],
        )

    return demo


if __name__ == "__main__":
    app = build_ui()
    app.launch(server_name="0.0.0.0", server_port=7860)
