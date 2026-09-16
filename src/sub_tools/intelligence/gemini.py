"""
Gemini provider: one subtitle request, one text-to-speech request.

The prompting, repair, and validation loop lives in pipeline.py; this module
only talks to the API.

Generation models are asked for SRT text directly. The dedicated transcription
models (Gemini 3.5 Transcribe) reject system instructions, thinking, and tools,
and answer with word-level timings instead, so their cues are assembled here.
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

# Model names that mean "speech-to-text only", e.g. gemini-3.5-transcribe. A
# hint rather than a closed list, so a renamed model keeps working.
TRANSCRIPTION_MODEL_HINTS = ("transcribe",)

# Subtitle shape for cues built from word timings, following the common
# broadcast conventions the reference subtitles also use.
MAX_LINE_CHARACTERS = 42
MAX_CUE_CHARACTERS = 2 * MAX_LINE_CHARACTERS
MAX_CUE_SECONDS = 5.0
MIN_CUE_CHARACTERS = 20
CUE_BREAK_GAP_SECONDS = 0.6
SENTENCE_ENDINGS = (".", "!", "?", "…")

# The TTS endpoint returns raw PCM at this shape.
TTS_SAMPLE_RATE = 24_000

# Token and character counts per model, for cost accounting. TTS characters
# are tracked because that is what pricing quotes.
usage: dict[str, dict] = {}

_uploaded_files: dict[str, types.File] = {}


def uses_transcription_api(model: str) -> bool:
    """
    Whether the model is a dedicated transcription model rather than a
    generation model that happens to accept audio.
    """
    return any(hint in model.lower() for hint in TRANSCRIPTION_MODEL_HINTS)


def accepts_audio() -> bool:
    """
    Gemini generation models hear audio natively.
    """
    return True


def can_transcribe_audio() -> bool:
    """Gemini generation models accept audio input natively."""
    return True


def prepare_audio() -> types.File:
    """
    Upload the configured audio file once and reuse it across requests.
    """
    path = config.audio_file
    if path not in _uploaded_files:
        client = genai.Client(api_key=config.api_key)
        _uploaded_files[path] = client.files.upload(file=path)
    return _uploaded_files[path]


async def generate(
    system_instruction: str,
    text: Optional[str] = None,
    with_audio: bool = True,
    thinking_level: str | None = None,
) -> Optional[str]:
    """
    Ask Gemini once for subtitles, retrying only transient server-side failures.

    ``thinking_level`` is selected by the pipeline per task: transcription
    defaults to HIGH for timing quality, while translation defaults to LOW.
    """
    client = genai.Client(api_key=config.api_key)
    transcription_only = with_audio and uses_transcription_api(config.model)

    parts = [prepare_audio()] if with_audio else []
    # A transcription model takes the audio and its own config; prompt text is
    # rejected rather than followed.
    if text and not transcription_only:
        parts.append(types.Part.from_text(text=text))

    tools = [
        types.Tool(google_search=types.GoogleSearch()),
    ]

    for attempt in range(config.retry):
        try:
            if transcription_only:
                return await _transcribe(client, parts)

            response = await client.aio.models.generate_content(
                model=config.model,
                contents=parts,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    thinking_config=types.ThinkingConfig(
                        include_thoughts=True,
                        thinking_level=_thinking_level(thinking_level or "high"),
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


async def _transcribe(client: genai.Client, parts: list) -> Optional[str]:
    """
    Transcribe with a speech-to-text model and build the SRT from word timings.

    The model returns words with offsets rather than subtitle text, so no
    prompt asks it for a container; the cues are grouped here instead.
    """
    response = await client.aio.models.generate_content(
        model=config.model,
        contents=parts,
        config=types.GenerateContentConfig(
            audio_transcription_config=types.AudioTranscriptionConfig(
                language_codes=[config.source_language],
                word_timestamp=True,
                # Timestamps are only available in verbatim mode.
                mode=types.AudioTranscriptionConfigMode.VERBATIM,
            ),
        ),
    )
    _record_usage(response)

    words = _transcribed_words(response)
    if not words:
        # Returning whatever text came back lets the shared validation loop
        # explain that timestamped subtitles are required instead of inventing
        # timings here.
        return response.text
    return _words_to_srt(words)


def _transcribed_words(response) -> list[tuple[str, float, float]]:
    """
    Flatten the word timings out of every transcribed audio part.
    """
    words: list[tuple[str, float, float]] = []
    for candidate in response.candidates or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            transcription = getattr(part, "audio_transcription", None)
            for word in getattr(transcription, "words", None) or []:
                text = (word.word or "").strip()
                start = _offset_seconds(word.start_offset)
                end = _offset_seconds(word.end_offset)
                if not text or start is None:
                    continue
                words.append((text, start, end if end is not None else start))
    words.sort(key=lambda word: word[1])
    return words


def _offset_seconds(offset) -> Optional[float]:
    """
    Read a protobuf duration, which arrives as either a number or "12.3s".
    """
    if offset is None:
        return None
    if isinstance(offset, (int, float)):
        return float(offset)
    try:
        return float(str(offset).rstrip("s"))
    except ValueError:
        return None


def _words_to_srt(words: list[tuple[str, float, float]]) -> str:
    """
    Group timed words into subtitle cues.

    A cue ends at a sentence boundary, at a pause, or once it would grow past
    the length or duration a reader can follow.
    """
    cues: list[str] = []
    current: list[tuple[str, float, float]] = []

    def flush() -> None:
        if not current:
            return
        text = _wrap(" ".join(word for word, _, _ in current))
        start = _timestamp(current[0][1])
        end = _timestamp(max(current[-1][2], current[0][1] + 0.1))
        cues.append(f"{len(cues) + 1}\n{start} --> {end}\n{text}\n")
        current.clear()

    for index, (word, start, end) in enumerate(words):
        length = sum(len(w) + 1 for w, _, _ in current) + len(word)
        duration = end - current[0][1] if current else 0.0
        if current and (length > MAX_CUE_CHARACTERS or duration > MAX_CUE_SECONDS):
            flush()

        current.append((word, start, end))

        characters = sum(len(w) + 1 for w, _, _ in current) - 1
        if characters < MIN_CUE_CHARACTERS:
            continue
        next_start = words[index + 1][1] if index + 1 < len(words) else None
        ends_sentence = word.endswith(SENTENCE_ENDINGS)
        pauses = next_start is not None and next_start - end > CUE_BREAK_GAP_SECONDS
        if ends_sentence or pauses:
            flush()

    flush()
    return "\n".join(cues)


def _wrap(text: str) -> str:
    """
    Split a cue over two balanced lines once it is too long for one.
    """
    if len(text) <= MAX_LINE_CHARACTERS:
        return text

    words = text.split()
    best = None
    for index in range(1, len(words)):
        first = " ".join(words[:index])
        second = " ".join(words[index:])
        if len(first) > MAX_LINE_CHARACTERS:
            break
        score = abs(len(first) - len(second))
        if best is None or score < best[0]:
            best = (score, first, second)
    if best is None:
        return text
    return f"{best[1]}\n{best[2]}"


def _timestamp(seconds: float) -> str:
    """
    Format seconds as an SRT timestamp.
    """
    seconds = max(seconds, 0.0)
    milliseconds = int(round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole, milliseconds = divmod(milliseconds, 1_000)
    return f"{hours:02}:{minutes:02}:{whole:02},{milliseconds:03}"


def _thinking_level(value: str) -> types.ThinkingLevel:
    """
    Convert the CLI/config value to the installed SDK enum.

    google-genai 1.52 exposes LOW and HIGH for the Gemini models used here.
    Keep this conversion at the provider boundary so the rest of the pipeline
    remains provider-agnostic.
    """
    try:
        return types.ThinkingLevel[value.upper()]
    except KeyError as error:
        raise ValueError(f"Unsupported Gemini thinking level: {value!r}") from error


async def speak(text: str, language: str) -> bytes:
    """
    Turn one piece of text into speech, returned as WAV bytes.
    """
    client = genai.Client(api_key=config.api_key)

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
