# IntelliTube/intellitube_agents/tts.py
import hashlib
import os
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

# Official SDK (matches the API ref examples that use `import openai`)
import openai


@dataclass(frozen=True)
class TTSConfig:
    model: str = "tts-1-hd"          # good quality default
    voice: str = "alloy"
    speed: float = 1.1              # requested default
    response_format: str = "wav"    # easiest to concat + works well with Gradio Audio
    cache_dir: str | Path = "cache/tts"


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _chunk_text(text: str, max_chars: int = 3900) -> List[str]:
    """
    OpenAI TTS input max is 4096 chars. We keep margin and split on sentence-ish boundaries.
    """
    t = " ".join((text or "").strip().split())
    if not t:
        return []

    if len(t) <= max_chars:
        return [t]

    chunks: List[str] = []
    start = 0
    while start < len(t):
        end = min(start + max_chars, len(t))
        # try to cut at a boundary
        cut = end
        for sep in [". ", "! ", "? ", "\n", ", "]:
            idx = t.rfind(sep, start, end)
            if idx != -1 and idx > start + 400:
                cut = idx + len(sep)
                break
        chunk = t[start:cut].strip()
        if chunk:
            chunks.append(chunk)
        start = cut

    return chunks


def _ffmpeg_atempo_chain(speed: float) -> str:
    """
    ffmpeg atempo supports 0.5..2.0 per filter, so chain if needed.
    """
    if speed <= 0:
        speed = 1.0
    parts = []
    s = speed
    while s > 2.0:
        parts.append(2.0)
        s /= 2.0
    while s < 0.5:
        parts.append(0.5)
        s /= 0.5
    parts.append(s)
    return ",".join([f"atempo={p:.6f}" for p in parts])


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _adjust_speed_ffmpeg(in_wav: Path, out_wav: Path, speed: float) -> None:
    """
    Post-process WAV to exact speed using ffmpeg.
    """
    if abs(speed - 1.0) < 1e-6:
        out_wav.write_bytes(in_wav.read_bytes())
        return

    if not _ffmpeg_available():
        # fallback: return unmodified
        out_wav.write_bytes(in_wav.read_bytes())
        return

    filt = _ffmpeg_atempo_chain(speed)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(in_wav),
        "-filter:a", filt,
        str(out_wav),
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        # fallback: return unmodified
        out_wav.write_bytes(in_wav.read_bytes())


def _concat_wavs(wavs: List[Path], out_wav: Path) -> None:
    """
    Concatenate WAVs safely (assumes same params).
    """
    if not wavs:
        raise ValueError("No wav files to concat")

    with wave.open(str(wavs[0]), "rb") as w0:
        params = w0.getparams()

    with wave.open(str(out_wav), "wb") as wout:
        wout.setparams(params)
        for wp in wavs:
            with wave.open(str(wp), "rb") as wi:
                if wi.getparams() != params:
                    raise RuntimeError("WAV params mismatch across chunks; cannot concat safely.")
                frames = wi.readframes(wi.getnframes())
                wout.writeframes(frames)


def synthesize_tts_to_file(text: str, *, cfg: TTSConfig) -> Path:
    """
    Returns a cached WAV path for the given text+cfg.
    Uses OpenAI TTS then (optionally) ffmpeg speed adjustment for exact playback speed.
    """
    txt = (text or "").strip()
    if not txt:
        raise ValueError("Empty transcript for TTS")

    cache_dir = Path(cfg.cache_dir).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)

    key = _sha1(f"{cfg.model}|{cfg.voice}|{cfg.speed}|{cfg.response_format}|{txt}")
    final_path = cache_dir / f"{key}.wav"
    if final_path.exists() and final_path.stat().st_size > 0:
        return final_path

    chunks = _chunk_text(txt)
    if not chunks:
        raise ValueError("No TTS chunks")

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        raw_wavs: List[Path] = []

        # Generate per-chunk wavs
        for i, chunk in enumerate(chunks):
            raw = td_path / f"raw_{i}.wav"
            # speed is documented, but some models may ignore; we still apply post-ffmpeg.
            with openai.audio.speech.with_streaming_response.create(
                model=cfg.model,
                voice=cfg.voice,
                input=chunk,
                response_format=cfg.response_format,
                speed=float(cfg.speed),
            ) as resp:
                resp.stream_to_file(raw)
            raw_wavs.append(raw)

        merged = td_path / "merged.wav"
        if len(raw_wavs) == 1:
            merged.write_bytes(raw_wavs[0].read_bytes())
        else:
            _concat_wavs(raw_wavs, merged)

        # Ensure exact playback speed
        _adjust_speed_ffmpeg(merged, final_path, float(cfg.speed))

    return final_path
