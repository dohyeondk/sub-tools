import asyncio
import io
import os
import re
import subprocess
import tempfile
import wave
from typing import Callable, Optional

from google import genai
from google.api_core import exceptions as google_exceptions
from google.genai import types
from rich.progress import Progress

from sub_tools.system.console import info, warning
from sub_tools.system.file import should_skip
from sub_tools.system.language import get_language_name

from ..config import config
from ..media.converter import audio_duration
from ..subtitles.repair import repair_subtitles
from ..subtitles.validator import (
    Cue,
    SubtitleValidationError,
    find_problems,
    parse_strict,
)

PCM_SAMPLE_RATE = 24_000
PCM_SAMPLE_WIDTH = 2
PCM_CHANNELS = 1


def transcribe() -> None:
    """
    Transcribe the audio into subtitles using Gemini.
    """
    if should_skip(f"{config.source_language}.srt"):
        return

    asyncio.run(_transcribe())


async def _transcribe() -> None:
    info("Transcribing...")

    language_code = config.source_language
    language = get_language_name(language_code)

    system_instruction = f"""
    You are a professional transcriptionist.
    You will receive an audio file in {language}.

    Your task is to:
    1. Listen to the audio carefully
    2. Transcribe every spoken word accurately
    3. Split the transcript into subtitle cues that follow the speech
    4. Give every cue start and end timestamps that match when the words are spoken

    CRITICAL REQUIREMENTS:
    1. Output ONLY the SRT file. No code blocks, no explanations.
    2. Preserve the SRT format perfectly (number, timestamp, text, blank line)
    3. Every timestamp must be HH:MM:SS,mmm --> HH:MM:SS,mmm, always including the
       hours field, even after the first hour of audio
    4. Cover the entire recording from beginning to end, including the final minutes
    5. Use correct punctuation and capitalization
    6. The output must be valid SRT format

    Return the SRT file.
    """

    file = _upload_file(config.audio_file)
    await _generate_subtitles(
        output_file=f"{language_code}.srt",
        system_instruction=system_instruction,
        file=file,
        text=f"Transcribe this {language} audio into an SRT subtitle file.",
    )


def translate() -> None:
    """
    Translate the source subtitles into each target language using Gemini.
    """
    asyncio.run(_translate())


async def _translate() -> None:
    source_language_code = config.source_language
    source_file = f"{source_language_code}.srt"

    with open(source_file, "r", encoding="utf-8") as f:
        srt_content = f.read()

    target_language_codes = [
        language
        for language in config.languages
        if language != source_language_code and not should_skip(f"{language}.srt")
    ]

    if not target_language_codes:
        return

    info("Translating...")

    tasks = []

    with Progress() as progress:
        progress_task = progress.add_task("Translation", total=len(target_language_codes))

        file = _upload_file(config.audio_file)

        for language_code in target_language_codes:
            task = asyncio.create_task(
                _translate_language(
                    file=file,
                    srt_content=srt_content,
                    source_language_code=source_language_code,
                    target_language_code=language_code,
                    completion=lambda: progress.update(progress_task, advance=1),
                )
            )
            tasks.append(task)

        await asyncio.gather(*tasks)


async def _translate_language(
    file: types.File,
    srt_content: str,
    source_language_code: str,
    target_language_code: str,
    completion: Callable[[], None],
) -> None:
    source_language = get_language_name(source_language_code)
    target_language = get_language_name(target_language_code)

    system_instruction = f"""
    You are a professional translator specializing in subtitle translation.
    You will receive an {source_language} SRT subtitle file and the corresponding audio file.

    Your task is to:
    1. Translate the {source_language} subtitles to {target_language}
    2. Listen to the audio to understand context and tone
    3. Keep the exact same timing (timestamps) as the input SRT
    4. Ensure translations are natural and culturally appropriate for {target_language}

    CRITICAL REQUIREMENTS:
    1. Output ONLY the translated SRT file in {target_language}. No code blocks, no explanations.
    2. Keep ALL timestamps exactly as they are in the input SRT
    3. Return exactly the same number of cues as the input, in the same order
    4. Preserve the SRT format perfectly (number, timestamp, text, blank line)
    5. Only translate the text content, not the structure or timing
    6. All subtitle text must be in {target_language}

    Translation Guidelines:
    - Use natural, conversational {target_language}
    - Preserve the tone and meaning of the original {source_language}
    - Keep proper names in their original form unless they have standard {target_language} equivalents
    - Maintain [sound effects] in brackets
    - Use appropriate punctuation for {target_language}

    Return the translated SRT file in {target_language}.
    """

    await _generate_subtitles(
        output_file=f"{target_language_code}.srt",
        system_instruction=system_instruction,
        file=file,
        text=f"{source_language} SRT to translate:\n\n{srt_content}",
        reference=srt_content,
    )
    completion()


def dub() -> None:
    """
    Generate a simple spoken rendition of each translated subtitle file.

    Gemini 3.7 cannot return audio, and Gemini TTS models cannot accept the
    original audio. This task therefore sends the translated text alone to the
    separately configured TTS model. The result is coarse timeline-aligned
    narration, not a cue-timed dub.
    """
    asyncio.run(_dub())


async def _dub() -> None:
    target_language_codes = [
        language
        for language in config.languages
        if language != config.source_language and not should_skip(f"{language}.wav")
    ]

    if not target_language_codes:
        return

    info("Generating translated audio...")

    with Progress() as progress:
        progress_task = progress.add_task(
            "Translated audio", total=len(target_language_codes)
        )
        tasks = [
            asyncio.create_task(
                _generate_dub_language(
                    language_code,
                    completion=lambda: progress.update(progress_task, advance=1),
                )
            )
            for language_code in target_language_codes
        ]
        await asyncio.gather(*tasks)


async def _generate_dub_language(
    language_code: str,
    completion: Callable[[], None],
) -> None:
    subtitle_file = f"{language_code}.srt"
    with open(subtitle_file, "r", encoding="utf-8") as f:
        srt_content = f.read()

    duration = audio_duration(config.audio_file)
    if duration is None:
        raise RuntimeError(
            "Cannot synchronize translated audio without the original audio duration"
        )

    cues, errors = parse_strict(srt_content)
    if errors:
        details = "; ".join(errors)
        raise SubtitleValidationError(
            f"Cannot generate translated audio from {subtitle_file}: {details}"
        )
    validation_errors, _ = find_problems(srt_content, duration=duration)
    if validation_errors:
        details = "; ".join(validation_errors)
        raise SubtitleValidationError(
            f"Cannot synchronize translated audio from {subtitle_file}: {details}"
        )
    language = get_language_name(language_code)
    groups = _dub_groups(cues)
    segments: list[tuple[float, float, bytes]] = []
    for index, group in enumerate(groups, start=1):
        speech_text = "\n".join(cue.text.replace("\n", " ") for cue in group)
        prompt = (
            f"Synthesize speech in {language}. Read the actual transcript naturally "
            "and exactly. Do not add, remove, or translate any words.\n\n"
            f"ACTUAL TRANSCRIPT:\n{speech_text}"
        )
        info(f"{language_code}.wav: generating chunk {index}/{len(groups)}")
        audio, mime_type = await _call_tts_api(prompt)
        pcm, sample_rate = _pcm_audio(audio, mime_type)
        start = group[0].start
        end = min(max(cue.end for cue in group), duration)
        if start >= end:
            continue
        segments.append((start, end, _fit_pcm_duration(pcm, sample_rate, end - start)))

    _write_synced_audio(f"{language_code}.wav", segments, duration)
    completion()


def _dub_groups(cues: list[Cue]) -> list[list[Cue]]:
    """Group nearby cues into bounded TTS requests while preserving long gaps."""
    if config.dub_chunk_duration <= 0:
        raise ValueError("Dub chunk duration must be greater than zero")
    if config.dub_gap_threshold < 0:
        raise ValueError("Dub gap threshold cannot be negative")

    groups: list[list[Cue]] = []
    current: list[Cue] = []
    for cue in cues:
        if cue.end - cue.start > config.dub_chunk_duration:
            raise ValueError(
                f"Subtitle #{cue.index} spans {cue.end - cue.start:.1f}s, exceeding the "
                f"{config.dub_chunk_duration:.1f}s dub chunk duration"
            )

        if current:
            current_end = max(item.end for item in current)
            starts_after_gap = (
                cue.start - current_end >= config.dub_gap_threshold
            )
            exceeds_window = (
                max(current_end, cue.end) - current[0].start
                > config.dub_chunk_duration
            )
            if exceeds_window and cue.start < current_end:
                raise ValueError(
                    "Overlapping subtitle cues exceed the configured dub chunk "
                    "duration; increase --dub-chunk-duration or fix the subtitle timings"
                )
            if starts_after_gap or exceeds_window:
                groups.append(current)
                current = []
        current.append(cue)
    if current:
        groups.append(current)
    return groups


async def _call_tts_api(text: str) -> tuple[bytes, str]:
    """Ask the configured Gemini TTS model for one audio response."""
    client = genai.Client(api_key=config.gemini_api_key)
    attempts = max(1, config.retry)

    for attempt in range(attempts):
        try:
            response = await client.aio.models.generate_content(
                model=config.gemini_tts_model,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=config.gemini_tts_voice
                            )
                        )
                    ),
                ),
            )
            return _audio_response(response)
        except (
            google_exceptions.InternalServerError,
            google_exceptions.ResourceExhausted,
            google_exceptions.ServiceUnavailable,
        ):
            if attempt < attempts - 1:
                await asyncio.sleep(_backoff(attempt))
                continue
            raise
        except Exception as e:
            message = str(e)
            transient = any(status in message for status in ("429", "500", "503"))
            if transient and attempt < attempts - 1:
                await asyncio.sleep(_backoff(attempt))
                continue
            raise

    raise RuntimeError("Gemini TTS did not return a response")


def _audio_response(response: types.GenerateContentResponse) -> tuple[bytes, str]:
    """Extract audio bytes and their MIME type from a GenerateContent response."""
    candidates = response.candidates or []
    if not candidates or not candidates[0].content:
        raise RuntimeError("Gemini TTS response contained no audio")

    parts = candidates[0].content.parts or []
    blobs = [
        part.inline_data for part in parts if part.inline_data and part.inline_data.data
    ]
    if not blobs:
        raise RuntimeError("Gemini TTS response contained no audio")

    mime_types = {blob.mime_type for blob in blobs if blob.mime_type}
    if len(mime_types) > 1:
        raise RuntimeError("Gemini TTS response contained incompatible audio formats")
    return b"".join(blob.data for blob in blobs), next(
        iter(mime_types), "audio/L16;rate=24000"
    )


def _pcm_audio(audio: bytes, mime_type: str) -> tuple[bytes, int]:
    """Return mono 16-bit PCM data and its sample rate."""
    normalized_mime_type = mime_type.lower()
    if normalized_mime_type.startswith(("audio/wav", "audio/x-wav")):
        with wave.open(io.BytesIO(audio), "rb") as wav_file:
            if wav_file.getnchannels() != PCM_CHANNELS:
                raise RuntimeError("Gemini TTS returned non-mono WAV audio")
            if wav_file.getsampwidth() != PCM_SAMPLE_WIDTH:
                raise RuntimeError("Gemini TTS returned non-16-bit WAV audio")
            return wav_file.readframes(wav_file.getnframes()), wav_file.getframerate()

    if not normalized_mime_type.startswith(("audio/l16", "audio/pcm")):
        raise RuntimeError(f"Gemini TTS returned unsupported audio format: {mime_type}")
    rate_match = re.search(r"(?:^|;)\s*rate=(\d+)", normalized_mime_type)
    return audio, int(rate_match.group(1)) if rate_match else PCM_SAMPLE_RATE


def _atempo_filter(speed: float) -> str:
    """Build a portable FFmpeg atempo chain for the requested speed."""
    factors = []
    while speed < 0.5:
        factors.append(0.5)
        speed /= 0.5
    while speed > 2.0:
        factors.append(2.0)
        speed /= 2.0
    factors.append(speed)
    return ",".join(f"atempo={factor:.8f}" for factor in factors)


def _fit_pcm_duration(pcm: bytes, sample_rate: int, target_duration: float) -> bytes:
    """Time-stretch PCM to a subtitle window without changing pitch."""
    if not pcm or target_duration <= 0:
        raise RuntimeError("Cannot synchronize empty or zero-length dub audio")
    source_duration = len(pcm) / (sample_rate * PCM_SAMPLE_WIDTH * PCM_CHANNELS)
    speed = source_duration / target_duration
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "s16le",
        "-ar",
        str(sample_rate),
        "-ac",
        str(PCM_CHANNELS),
        "-i",
        "pipe:0",
        "-filter:a",
        _atempo_filter(speed),
        "-ar",
        str(PCM_SAMPLE_RATE),
        "-ac",
        str(PCM_CHANNELS),
        "-f",
        "s16le",
        "pipe:1",
    ]
    try:
        result = subprocess.run(cmd, input=pcm, check=True, capture_output=True)
    except FileNotFoundError as error:
        raise RuntimeError(
            "FFmpeg is required to synchronize translated audio"
        ) from error
    except subprocess.CalledProcessError as error:
        details = error.stderr.decode(errors="replace").strip()
        raise RuntimeError(
            f"Failed to synchronize translated audio: {details}"
        ) from error

    if not result.stdout:
        raise RuntimeError("FFmpeg returned no synchronized audio")
    target_bytes = round(target_duration * PCM_SAMPLE_RATE) * PCM_SAMPLE_WIDTH
    return result.stdout[:target_bytes].ljust(target_bytes, b"\0")


def _write_synced_audio(
    output_file: str,
    segments: list[tuple[float, float, bytes]],
    duration: float,
) -> None:
    """Write fitted speech at its timeline positions as an atomic WAV output."""
    directory = os.path.dirname(os.path.abspath(output_file))
    wav_temporary = tempfile.NamedTemporaryFile(
        prefix=".dub-", suffix=".wav", dir=directory, delete=False
    )
    wav_temporary.close()
    try:
        with wave.open(wav_temporary.name, "wb") as wav_file:
            wav_file.setnchannels(PCM_CHANNELS)
            wav_file.setsampwidth(PCM_SAMPLE_WIDTH)
            wav_file.setframerate(PCM_SAMPLE_RATE)
            position = 0
            for start, end, pcm in segments:
                start_frame = round(start * PCM_SAMPLE_RATE)
                end_frame = round(end * PCM_SAMPLE_RATE)
                if start_frame < position:
                    raise RuntimeError("Translated subtitle windows overlap")
                wav_file.writeframes(
                    b"\0" * ((start_frame - position) * PCM_SAMPLE_WIDTH)
                )
                target_bytes = (end_frame - start_frame) * PCM_SAMPLE_WIDTH
                wav_file.writeframes(pcm[:target_bytes].ljust(target_bytes, b"\0"))
                position = end_frame

            final_frame = round(duration * PCM_SAMPLE_RATE)
            if position > final_frame:
                raise RuntimeError(
                    "Translated audio extends beyond the source duration"
                )
            wav_file.writeframes(b"\0" * ((final_frame - position) * PCM_SAMPLE_WIDTH))
        os.replace(wav_temporary.name, output_file)
    finally:
        if os.path.exists(wav_temporary.name):
            os.unlink(wav_temporary.name)


async def _generate_subtitles(
    output_file: str,
    system_instruction: str,
    file: Optional[types.File] = None,
    text: Optional[str] = None,
    reference: Optional[str] = None,
) -> None:
    """
    Ask Gemini for subtitles, repairing and checking the answer before accepting it.

    Models get the words right far more reliably than the container, so a reply
    that fails to parse is repaired first and only re-requested if the repair
    cannot save it.
    """
    duration = audio_duration(config.audio_file)
    attempts = max(1, config.retry)
    last_errors: list[str] = []

    for attempt in range(attempts):
        content = await _call_gemini_api(
            system_instruction=system_instruction,
            file=file,
            text=text,
        )

        if not content or "-->" not in content:
            last_errors = ["response contained no subtitles"]
            _report_attempt(output_file, attempt, attempts, last_errors)
            continue

        repaired, notes = repair_subtitles(content, duration=duration, reference=reference)
        errors, warnings = find_problems(repaired, duration=duration, reference=reference)

        if errors:
            last_errors = errors
            _report_attempt(output_file, attempt, attempts, errors)
            continue

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(repaired)

        for note in notes:
            info(f"{output_file}: repaired — {note}")
        for message in warnings:
            warning(f"{output_file}: {message}")
        return

    raise SubtitleValidationError(
        f"Could not produce valid subtitles for {output_file} "
        f"after {attempts} attempt(s): {'; '.join(last_errors)}"
    )


def _report_attempt(output_file: str, attempt: int, attempts: int, errors: list[str]) -> None:
    """
    Explain why an answer was rejected before asking again.
    """
    reason = "; ".join(errors)
    if attempt + 1 < attempts:
        warning(f"{output_file}: attempt {attempt + 1}/{attempts} rejected ({reason}); retrying")
    else:
        warning(f"{output_file}: attempt {attempt + 1}/{attempts} rejected ({reason})")


async def _call_gemini_api(
    system_instruction: str,
    file: Optional[types.File] = None,
    text: Optional[str] = None,
) -> Optional[str]:
    """
    Call the Gemini API once, retrying only transient server-side failures.
    """
    client = genai.Client(api_key=config.gemini_api_key)

    parts = []
    if file:
        parts.append(file)
    if text:
        parts.append(types.Part.from_text(text=text))

    tools = [
        types.Tool(google_search=types.GoogleSearch()),
    ]

    for attempt in range(config.retry):
        try:
            response = await client.aio.models.generate_content(
                model=config.gemini_model,
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
            return response.text

        except (google_exceptions.ResourceExhausted, google_exceptions.ServiceUnavailable) as e:
            if attempt < config.retry - 1:
                await asyncio.sleep(_backoff(attempt))
                continue
            raise e
        except Exception as e:
            message = str(e)
            # The SDK surfaces 429/503 as generic errors depending on transport.
            if ("429" in message or "503" in message) and attempt < config.retry - 1:
                await asyncio.sleep(_backoff(attempt))
                continue
            raise e

    return None


def _backoff(attempt: int) -> int:
    """
    Wait long enough for a capacity problem to clear.

    "High demand" responses persist for far longer than the one to four seconds
    an unscaled backoff would wait.
    """
    return min(60, 5 * 2**attempt)


def _upload_file(file_path: str) -> types.File:
    client = genai.Client(api_key=config.gemini_api_key)
    file = client.files.upload(file=file_path)
    return file
