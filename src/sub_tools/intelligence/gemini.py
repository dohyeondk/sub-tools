"""
Gemini provider: one subtitle request, one text-to-speech request.

The prompting, repair, and validation loop lives in pipeline.py; this module
only talks to the API.
"""

import asyncio
import io
import wave
from typing import Optional

from google import genai
from google.api_core import exceptions as google_exceptions
from google.genai import types

from ..config import config
from .retry import backoff

DEFAULT_TTS_MODEL = "gemini-2.5-flash-preview-tts"
DEFAULT_TTS_VOICE = "Sadaltager"

# The TTS endpoint returns raw PCM at this shape.
TTS_SAMPLE_RATE = 24_000

# Token and character counts per model, for cost accounting. TTS characters
# are tracked because that is what pricing quotes.
usage: dict[str, dict] = {}

_uploaded_files: dict[str, types.File] = {}


def accepts_audio() -> bool:
    """
    Gemini generation models hear audio natively.
    """
    return True


def prepare_audio() -> types.File:
    """
    Upload the configured audio file once and reuse it across requests.
    """
    path = config.audio_file
    if path not in _uploaded_files:
        client = genai.Client(api_key=config.gemini_api_key)
        _uploaded_files[path] = client.files.upload(file=path)
    return _uploaded_files[path]


async def generate(
    system_instruction: str,
    text: Optional[str] = None,
    with_audio: bool = True,
) -> Optional[str]:
    """
    Ask Gemini once for subtitles, retrying only transient server-side failures.
    """
    client = genai.Client(api_key=config.gemini_api_key)

    parts = [prepare_audio()] if with_audio else []
    if text:
        parts.append(types.Part.from_text(text=text))

    tools = [
        types.Tool(google_search=types.GoogleSearch()),
    ]

    for attempt in range(config.retry):
        try:
            response = await client.aio.models.generate_content(
                model=config.model,
                contents=parts,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    thinking_config=types.ThinkingConfig(
                        include_thoughts=True,
                        thinking_level=types.ThinkingLevel.HIGH,
                    ),
                    tools=tools,
                ),
            )
            _record_usage(response)
            return response.text

        except (google_exceptions.ResourceExhausted, google_exceptions.ServiceUnavailable) as e:
            if attempt < config.retry - 1:
                await asyncio.sleep(backoff(attempt))
                continue
            raise e
        except Exception as e:
            message = str(e)
            # The SDK surfaces 429/503 as generic errors depending on transport.
            if ("429" in message or "503" in message) and attempt < config.retry - 1:
                await asyncio.sleep(backoff(attempt))
                continue
            raise e

    return None


async def speak(text: str, language: str) -> bytes:
    """
    Turn one piece of text into speech, returned as WAV bytes.
    """
    client = genai.Client(api_key=config.gemini_api_key)

    voice = config.tts_voice or DEFAULT_TTS_VOICE
    response = await client.aio.models.generate_content(
        model=config.tts_model or DEFAULT_TTS_MODEL,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice),
                ),
            ),
        ),
    )

    model = config.tts_model or DEFAULT_TTS_MODEL
    bucket = _bucket(model)
    bucket["requests"] += 1
    bucket["tts_characters"] += len(text)
    meta = getattr(response, "usage_metadata", None)
    if meta and meta.candidates_token_count:
        bucket["tts_output_tokens"] += meta.candidates_token_count

    pcm = response.candidates[0].content.parts[0].inline_data.data
    return _pcm_to_wav(pcm)


def _bucket(model: str) -> dict:
    return usage.setdefault(
        model,
        {
            "requests": 0,
            "input_tokens": 0,
            "audio_input_tokens": 0,
            "output_tokens": 0,
            "tts_characters": 0,
            "tts_output_tokens": 0,
        },
    )


def _record_usage(response) -> None:
    meta = getattr(response, "usage_metadata", None)
    if not meta:
        return
    bucket = _bucket(config.model)
    bucket["requests"] += 1
    bucket["input_tokens"] += meta.prompt_token_count or 0
    bucket["output_tokens"] += (meta.candidates_token_count or 0) + (
        meta.thoughts_token_count or 0
    )
    for detail in meta.prompt_tokens_details or []:
        if detail.modality == types.MediaModality.AUDIO:
            bucket["audio_input_tokens"] += detail.token_count or 0


def _pcm_to_wav(pcm: bytes) -> bytes:
    """
    Wrap the raw 16-bit mono PCM that the TTS endpoint returns in a WAV header.
    """
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(TTS_SAMPLE_RATE)
        wav.writeframes(pcm)
    return buffer.getvalue()
