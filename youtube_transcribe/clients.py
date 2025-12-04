import os
from dataclasses import dataclass
from typing import Optional, Any
from pathlib import Path
from dotenv import load_dotenv

@dataclass(frozen=True)
class OpenAITranscribeConfig:
    model: str = "whisper-1"  # can also be "gpt-4o-transcribe" / "gpt-4o-mini-transcribe"
    response_format: str = "text"  # simplest for downstream usage


class OpenAIWhisperClient:
    """OpenAI speech-to-text client (Whisper / GPT-4o Transcribe family).

    Auth:
      - set OPENAI_API_KEY in env, or pass api_key=
      - optionally pass base_url= for proxies
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        config: Optional[OpenAITranscribeConfig] = None,
    ) -> None:
        self._config = config or OpenAITranscribeConfig()

        try:
            from openai import OpenAI  # type: ignore
        except Exception as e:
            raise ImportError(
                "Missing dependency 'openai'. Install with: pip install openai"
            ) from e

        load_dotenv()

        resolved_key = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
        if not resolved_key:
            raise RuntimeError(
                "OpenAI API key not found. Set OPENAI_API_KEY in your environment or in a .env file."
            )

        try:
            from openai import OpenAI  # type: ignore
        except Exception as e:
            raise ImportError("Missing dependency 'openai'. Install with: pip install openai") from e

        kwargs: dict[str, Any] = {"api_key": resolved_key}
        if base_url:
            kwargs["base_url"] = base_url

        self._client = OpenAI(**kwargs)

    def transcribe(
        self,
        audio_path: str,
        *,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> str:
        p = Path(audio_path).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"Audio file not found: {p}")

        with p.open("rb") as audio_file:
            # OpenAI Python SDK: client.audio.transcriptions.create(...)
            res = self._client.audio.transcriptions.create(
                model=self._config.model,
                file=audio_file,
                response_format=self._config.response_format,
                language=language,
                prompt=prompt,
            )

        # response_format="text" can be a raw string; otherwise it may be an object/dict with .text
        if isinstance(res, str):
            return res

        txt = getattr(res, "text", None)
        if isinstance(txt, str):
            return txt

        # fallback for dict-like responses
        try:
            t2 = res.get("text")  # type: ignore[attr-defined]
            if isinstance(t2, str):
                return t2
        except Exception:
            pass

        return str(res)
