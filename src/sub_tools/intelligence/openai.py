"""
OpenAI provider: one subtitle request, one text-to-speech request.

Selected by naming an OpenAI model, e.g. --model gpt-5.6-luna. Text models
cannot hear audio, so requests that need it are routed to an audio model
(gpt-audio-1.5 unless --audio-model says otherwise) while the selected model
keeps the text-only work, such as translation.

The audio is inlined into each request as base64 rather than uploaded, so
recordings that would blow the request cap are first re-encoded at a speech
bitrate; that keeps roughly an hour of audio within one call.
"""

import asyncio
import base64
import os
import subprocess
import tempfile
from typing import Optional

import openai
from openai import AsyncOpenAI

from ..config import config
from ..system.console import info
from .retry import backoff

DEFAULT_AUDIO_MODEL = "whisper-1"
DEFAULT_TTS_MODEL = "gpt-4o-mini-tts"
DEFAULT_TTS_VOICE = "alloy"

# Model families that accept audio input in chat; everything else is text-only.
AUDIO_MODEL_PREFIXES = ("gpt-audio", "gpt-4o-audio", "gpt-realtime")

# Model families served by the dedicated transcription endpoint, which returns
# SRT directly. Chat audio models (gpt-audio-*) can follow instructions but
# stop transcribing partway through long recordings; the purpose-built ASR
# models do not.
TRANSCRIPTION_API_PREFIXES = ("whisper", "gpt-4o-transcribe", "gpt-4o-mini-transcribe")

# The API caps inlined audio at 20 MB. Base64 grows data by a third, so the
# file itself must stay under this for the request to fit.
MAX_FILE_BYTES = 15 * 1024 * 1024

# Mono speech at this rate stays intelligible to the model and fits about an
# hour of audio under the cap (32 kbit/s ≈ 14.4 MB/hour).
COMPRESS_BITRATE = "32k"
COMPRESS_SAMPLE_RATE = 16_000

# Token and character counts per model, for cost accounting. TTS is billed by
# input character, not by returned audio.
usage: dict[str, dict] = {}

_audio_cache: dict[str, tuple[str, str]] = {}


def accepts_audio() -> bool:
    """
    Whether the selected model can hear audio itself.
    """
    return config.model.lower().startswith(AUDIO_MODEL_PREFIXES)


def uses_transcription_api(model: str) -> bool:
    """
    Whether a model is served by the dedicated transcription endpoint.
    """
    return model.lower().startswith(TRANSCRIPTION_API_PREFIXES)


def generation_model(with_audio: bool) -> str:
    """
    The model a request should go to: audio requests from a text-only model
    are routed to the audio model.
    """
    if with_audio and not accepts_audio():
        return config.audio_model or DEFAULT_AUDIO_MODEL
    return config.model


_send_files: dict[str, tuple[str, str]] = {}


def _send_file() -> tuple[str, str]:
    """
    The file to actually send, as (path, format).

    Files too large to send are re-encoded for speech first; only a file that
    stays oversized after that is refused.
    """
    path = config.audio_file
    if path not in _send_files:
        send_path, extension = path, _extension(path)
        if os.path.getsize(path) > MAX_FILE_BYTES:
            send_path, extension = _compress(path), "mp3"
            if os.path.getsize(send_path) > MAX_FILE_BYTES:
                raise RuntimeError(
                    f"{path} is still too large for OpenAI audio input after "
                    f"re-encoding at {COMPRESS_BITRATE}bit/s; the cap allows about "
                    f"an hour of speech. Use a Gemini model for this file."
                )
        _send_files[path] = (send_path, extension)
    return _send_files[path]


def prepare_audio() -> tuple[str, str]:
    """
    Read and base64-encode the configured audio file once, returning (data, format).
    """
    path = config.audio_file
    if path not in _audio_cache:
        send_path, extension = _send_file()
        with open(send_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        _audio_cache[path] = (data, extension)
    return _audio_cache[path]


def _extension(path: str) -> str:
    return os.path.splitext(path)[1].lstrip(".").lower() or "mp3"


def _compress(path: str) -> str:
    """
    Re-encode the audio as mono low-bitrate MP3 so it fits in one request.
    """
    fd, compressed = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    cmd = [
        "ffmpeg", "-y", "-i", path,
        "-ac", "1", "-ar", str(COMPRESS_SAMPLE_RATE), "-b:a", COMPRESS_BITRATE,
        compressed,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        stderr = e.stderr.decode() if getattr(e, "stderr", None) else str(e)
        raise RuntimeError(f"Failed to compress {path} for OpenAI audio input: {stderr}")

    info(
        f"Compressed {path} for OpenAI audio input: "
        f"{os.path.getsize(path) / 1024 / 1024:.1f} MB → "
        f"{os.path.getsize(compressed) / 1024 / 1024:.1f} MB"
    )
    return compressed


async def generate(
    system_instruction: str,
    text: Optional[str] = None,
    with_audio: bool = True,
) -> Optional[str]:
    """
    Ask the model once for subtitles, retrying only transient failures.
    """
    model = generation_model(with_audio)
    if with_audio and model != config.model:
        info(f"{config.model} cannot hear audio; listening with {model}")

    if with_audio and uses_transcription_api(model):
        return await _transcribe_via_api(model)

    content: list[dict] = []
    if with_audio:
        data, audio_format = prepare_audio()
        content.append(
            {"type": "input_audio", "input_audio": {"data": data, "format": audio_format}}
        )
    if text:
        content.append({"type": "text", "text": text})

    kwargs = {"modalities": ["text"]} if with_audio else {}

    async with AsyncOpenAI(api_key=config.openai_api_key) as client:
        for attempt in range(config.retry):
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": content},
                    ],
                    **kwargs,
                )
                _record_usage(model, response.usage)
                return response.choices[0].message.content

            except (
                openai.RateLimitError,
                openai.InternalServerError,
                openai.APIConnectionError,
            ) as e:
                if attempt < config.retry - 1:
                    await asyncio.sleep(backoff(attempt))
                    continue
                raise e

    return None


async def _transcribe_via_api(model: str) -> Optional[str]:
    """
    Transcribe through the dedicated endpoint, which answers in SRT directly.

    The endpoint is billed by audio minute, so seconds are tallied instead of
    tokens.
    """
    from ..media.converter import audio_duration

    send_path, _ = _send_file()

    async with AsyncOpenAI(api_key=config.openai_api_key) as client:
        for attempt in range(config.retry):
            try:
                with open(send_path, "rb") as f:
                    result = await client.audio.transcriptions.create(
                        model=model,
                        file=f,
                        response_format="srt",
                        language=config.source_language,
                    )
                bucket = _bucket(model)
                bucket["requests"] += 1
                bucket["transcribe_seconds"] += audio_duration(config.audio_file) or 0
                return result if isinstance(result, str) else getattr(result, "text", None)

            except (
                openai.RateLimitError,
                openai.InternalServerError,
                openai.APIConnectionError,
            ) as e:
                if attempt < config.retry - 1:
                    await asyncio.sleep(backoff(attempt))
                    continue
                raise e

    return None


async def speak(text: str, language: str) -> bytes:
    """
    Turn one piece of text into speech, returned as WAV bytes.
    """
    model = config.tts_model or DEFAULT_TTS_MODEL

    async with AsyncOpenAI(api_key=config.openai_api_key) as client:
        response = await client.audio.speech.create(
            model=model,
            voice=config.tts_voice or DEFAULT_TTS_VOICE,
            input=text,
            instructions=f"Speak naturally in {language}, matching the pace of subtitles.",
            response_format="wav",
        )
        data = response.read()

    bucket = _bucket(model)
    bucket["requests"] += 1
    bucket["tts_characters"] += len(text)
    return data


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
    bucket["input_tokens"] += response_usage.prompt_tokens or 0
    bucket["output_tokens"] += response_usage.completion_tokens or 0
    details = getattr(response_usage, "prompt_tokens_details", None)
    if details and getattr(details, "audio_tokens", None):
        bucket["audio_input_tokens"] += details.audio_tokens
