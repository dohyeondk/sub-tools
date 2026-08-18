"""
Anthropic provider for text generation.

Claude's Messages API is useful for translation and other text-only subtitle
work, but it does not accept audio input or provide text-to-speech. Users who
want Claude's reasoning with audio should select an equivalent Claude model
through OpenRouter instead.
"""

import asyncio

import anthropic
from anthropic import AsyncAnthropic

from ..config import config
from .retry import backoff

MAX_OUTPUT_TOKENS = 16_384

usage: dict[str, dict] = {}


def accepts_audio() -> bool:
    """Anthropic's native Messages API is text/image input, not audio input."""
    return False


def can_transcribe_audio() -> bool:
    """Anthropic cannot transcribe audio through its native API."""
    return False


def prepare_audio() -> None:
    """Keep the provider interface uniform; no audio upload is needed."""
    return


async def generate(
    system_instruction: str,
    text: str | None = None,
    with_audio: bool = True,
) -> str | None:
    """Ask Claude for one text-only subtitle response."""
    if with_audio:
        raise RuntimeError(
            "Anthropic models do not accept audio input; use an audio-capable "
            "provider for transcription."
        )

    prompt = text or ""
    for attempt in range(max(1, config.retry)):
        try:
            async with AsyncAnthropic(api_key=config.api_key) as client:
                response = await client.messages.create(
                    model=config.model,
                    max_tokens=MAX_OUTPUT_TOKENS,
                    system=system_instruction,
                    messages=[{"role": "user", "content": prompt}],
                )
            _record_usage(response)
            return "".join(
                block.text
                for block in response.content
                if getattr(block, "type", None) == "text"
            )
        except _RETRYABLE_ERRORS as error:
            if attempt < config.retry - 1:
                await asyncio.sleep(backoff(attempt))
                continue
            raise error

    return None


async def speak(text: str, language: str) -> bytes:
    """Anthropic has no native text-to-speech endpoint."""
    raise RuntimeError(
        "Anthropic does not provide text-to-speech through its API; select a "
        "provider with a TTS model for the dub task."
    )


def _bucket(model: str) -> dict:
    return usage.setdefault(
        model,
        {
            "requests": 0,
            "input_tokens": 0,
            "audio_input_tokens": 0,
            "output_tokens": 0,
            "tts_characters": 0,
        },
    )


def _record_usage(response) -> None:
    bucket = _bucket(config.model)
    bucket["requests"] += 1
    response_usage = getattr(response, "usage", None)
    if response_usage:
        bucket["input_tokens"] += getattr(response_usage, "input_tokens", 0) or 0
        bucket["output_tokens"] += getattr(response_usage, "output_tokens", 0) or 0


_RETRYABLE_ERRORS = (
    anthropic.RateLimitError,
    anthropic.InternalServerError,
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
)
