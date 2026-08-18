"""
OpenRouter provider.

OpenRouter's official Python SDK exposes async chat, speech-to-text, and
text-to-speech methods. Audio-capable chat models can return timestamped SRT
directly; dedicated speech-to-text models are also supported when their response
includes timestamped segments.
"""

import base64
import os
import subprocess
import tempfile
from typing import Any

from openrouter import OpenRouter

from ..config import config
from ..system.console import info

DEFAULT_AUDIO_MODEL = "google/gemini-2.5-flash"
DEFAULT_TTS_MODEL = "openai/gpt-4o-mini-tts"
DEFAULT_TTS_VOICE = "alloy"

# These are hints rather than a closed model registry. OpenRouter adds models
# frequently, and --audio-model is available for a model with a new name.
AUDIO_MODEL_HINTS = (
    "audio",
    "gemini",
    "gpt-4o",
    "omni",
    "qwen2-audio",
    "qwen3-omni",
    "voxtral",
    "realtime",
)
TRANSCRIPTION_MODEL_HINTS = (
    "whisper",
    "transcrib",
    "parakeet",
    "moonshine",
    "canary",
    "speech-to-text",
    "stt",
)

# Keep requests reasonably sized for providers behind OpenRouter. Audio input
# is base64-encoded, so a 15 MB source remains a safe size for most contexts.
MAX_FILE_BYTES = 15 * 1024 * 1024
COMPRESS_BITRATE = "32k"
COMPRESS_SAMPLE_RATE = 16_000

usage: dict[str, dict] = {}
_send_files: dict[str, tuple[str, str]] = {}
_audio_cache: dict[str, tuple[str, str]] = {}


def accepts_audio() -> bool:
    """Whether the selected model is likely to accept chat audio input."""
    model = _model_leaf(config.model)
    return _has_hint(model, AUDIO_MODEL_HINTS) and not uses_transcription_api(
        config.model
    )


def can_transcribe_audio() -> bool:
    """OpenRouter provides chat-audio and dedicated speech-to-text routes."""
    return True


def uses_transcription_api(model: str) -> bool:
    """Whether a model looks like a dedicated OpenRouter STT model."""
    return _has_hint(_model_leaf(model), TRANSCRIPTION_MODEL_HINTS)


def generation_model(with_audio: bool) -> str:
    """Choose the configured model or an audio model for an audio request."""
    if with_audio and uses_transcription_api(config.model):
        return config.model
    if with_audio and not accepts_audio():
        return config.audio_model or DEFAULT_AUDIO_MODEL
    return config.model


def prepare_audio() -> tuple[str, str]:
    """Read and base64-encode the configured audio file once."""
    path = config.audio_file
    if path not in _audio_cache:
        send_path, extension = _send_file()
        with open(send_path, "rb") as audio:
            data = base64.b64encode(audio.read()).decode("ascii")
        _audio_cache[path] = (data, extension)
    return _audio_cache[path]


async def generate(
    system_instruction: str,
    text: str | None = None,
    with_audio: bool = True,
) -> str | None:
    """Ask one OpenRouter model for subtitles using the SDK retry policy."""
    model = generation_model(with_audio)
    if with_audio and model != config.model:
        info(f"{config.model} cannot hear audio; listening with {model}")

    if with_audio and uses_transcription_api(model):
        return await _transcribe_via_api(model)

    content: str | list[dict[str, Any]]
    if with_audio:
        data, audio_format = prepare_audio()
        content = [
            {
                "type": "input_audio",
                "input_audio": {"data": data, "format_": audio_format},
            }
        ]
        if text:
            content.append({"type": "text", "text": text})
    else:
        content = text or ""

    async with _client() as client:
        response = await client.chat.send_async(
            model=model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": content},
            ],
            stream=False,
        )
    _record_usage(model, response.usage)
    return _message_text(response.choices[0].message)


async def _transcribe_via_api(model: str) -> str | None:
    """Use OpenRouter's SDK STT endpoint and preserve returned segments."""
    send_path, _ = _send_file()
    async with _client() as client:
        with open(send_path, "rb") as audio:
            result = await client.stt.create_transcription_multipart_async(
                file={"file_name": os.path.basename(send_path), "content": audio},
                model=model,
                language=config.source_language,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )

    _record_transcription_usage(model, result.usage)
    if result.segments:
        return _segments_to_srt(result.segments)
    # Non-OpenAI-compatible STT providers may return text only. Returning it
    # lets the shared validation loop explain that timestamped SRT is required
    # instead of silently inventing timings.
    return result.text


async def speak(text: str, language: str) -> bytes:
    """Generate speech through OpenRouter's TTS endpoint."""
    model = config.tts_model or DEFAULT_TTS_MODEL
    async with _client() as client:
        response = await client.tts.create_speech_async(
            model=model,
            input=text,
            voice=config.tts_voice or DEFAULT_TTS_VOICE,
            response_format="mp3",
        )
        await response.aread()
        data = response.content

    bucket = _bucket(model)
    bucket["requests"] += 1
    bucket["tts_characters"] += len(text)
    return data


def _client() -> OpenRouter:
    return OpenRouter(
        api_key=config.api_key,
        http_referer="https://github.com/dohyeondk/sub-tools",
        x_open_router_title="sub-tools",
    )


def _model_leaf(model: str) -> str:
    return model.rsplit("/", 1)[-1].lower()


def _has_hint(model: str, hints: tuple[str, ...]) -> bool:
    return any(hint in model for hint in hints)


def _send_file() -> tuple[str, str]:
    path = config.audio_file
    if path not in _send_files:
        send_path, extension = path, _extension(path)
        if os.path.getsize(path) > MAX_FILE_BYTES:
            send_path = _compress(path)
            extension = "mp3"
            if os.path.getsize(send_path) > MAX_FILE_BYTES:
                raise RuntimeError(
                    f"{path} is still too large for OpenRouter audio input after "
                    f"re-encoding at {COMPRESS_BITRATE}bit/s"
                )
        _send_files[path] = (send_path, extension)
    return _send_files[path]


def _extension(path: str) -> str:
    return os.path.splitext(path)[1].lstrip(".").lower() or "mp3"


def _compress(path: str) -> str:
    fd, compressed = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    cmd = [
        "ffmpeg", "-y", "-i", path,
        "-ac", "1", "-ar", str(COMPRESS_SAMPLE_RATE), "-b:a", COMPRESS_BITRATE,
        compressed,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as error:
        stderr = error.stderr.decode() if getattr(error, "stderr", None) else str(error)
        raise RuntimeError(
            f"Failed to compress {path} for OpenRouter audio input: {stderr}"
        )
    return compressed


def _message_text(message) -> str | None:
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
            elif isinstance(getattr(item, "text", None), str):
                parts.append(item.text)
        return "".join(parts) or None
    return None


def _segments_to_srt(segments: list[Any]) -> str:
    cues = []
    for segment in segments:
        start_seconds = float(_field(segment, "start", 0))
        end_seconds = float(_field(segment, "end", start_seconds))
        start = _timestamp(start_seconds)
        end = _timestamp(end_seconds)
        text = str(_field(segment, "text", "")).strip()
        if text:
            cues.append(f"{len(cues) + 1}\n{start} --> {end}\n{text}\n")
    return "\n".join(cues)


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def _bucket(model: str) -> dict:
    return usage.setdefault(
        model,
        {
            "requests": 0,
            "input_tokens": 0,
            "audio_input_tokens": 0,
            "output_tokens": 0,
            "tts_characters": 0,
            "transcribe_seconds": 0,
        },
    )


def _record_usage(model: str, response_usage) -> None:
    if not response_usage:
        return
    bucket = _bucket(model)
    bucket["requests"] += 1
    bucket["input_tokens"] += getattr(response_usage, "prompt_tokens", 0) or getattr(
        response_usage, "input_tokens", 0
    ) or 0
    bucket["output_tokens"] += (
        getattr(response_usage, "completion_tokens", 0)
        or getattr(response_usage, "output_tokens", 0)
        or 0
    )
    details = getattr(response_usage, "prompt_tokens_details", None)
    if details and getattr(details, "audio_tokens", None):
        bucket["audio_input_tokens"] += details.audio_tokens


def _record_transcription_usage(model: str, response_usage: Any) -> None:
    bucket = _bucket(model)
    bucket["requests"] += 1
    if response_usage:
        bucket["input_tokens"] += _field(response_usage, "input_tokens", 0) or 0
        bucket["output_tokens"] += _field(response_usage, "output_tokens", 0) or 0
        bucket["transcribe_seconds"] += _field(response_usage, "seconds", 0) or 0
