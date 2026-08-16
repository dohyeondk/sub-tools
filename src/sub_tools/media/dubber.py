"""
Dub subtitles back into audio.

Each cue of a translated SRT file is spoken by the provider's text-to-speech
model, sped up if it does not fit the time the original speaker took, and
placed at the cue's start time over silence. The result is an MP3 the same
length as the original recording, so it can be laid straight over the video.

The timing rules are deliberately simple:

  - a cue's slot runs from its start to the next cue's start (or the end of
    the audio, for the last cue)
  - speech longer than its slot is sped up, but never more than MAX_TEMPO,
    because faster than that is noise, not narration
  - speech that still overruns pushes later cues back rather than talking
    over them; the drift is bounded by MAX_TEMPO
  - text that is only a [sound effect] is not spoken
"""

import asyncio
import io
import os
import re
import subprocess
import tempfile
import wave

from rich.progress import Progress

from ..config import config
from ..intelligence.pipeline import get_provider
from ..intelligence.retry import backoff
from .converter import audio_duration
from ..subtitles.validator import Cue, SubtitleValidationError, parse_strict
from ..system.console import info, warning
from ..system.file import should_skip
from ..system.language import get_language_name

SAMPLE_RATE = 24_000
SAMPLE_WIDTH = 2  # 16-bit PCM
CHANNELS = 1

MAX_TEMPO = 2.0  # Fastest acceptable speed-up for overlong speech
CONCURRENT_REQUESTS = 4

BRACKETED = re.compile(r"\[[^\]]*\]|\([^)]*\)")


def dub() -> None:
    """
    Generate a dubbed MP3 for every requested language that has subtitles.
    """
    languages = [
        language
        for language in config.languages
        if not should_skip(f"{language}.mp3")
    ]

    if not languages:
        return

    for language in languages:
        if not os.path.exists(f"{language}.srt"):
            raise FileNotFoundError(
                f"{language}.srt not found; run the transcribe/translate tasks first"
            )

    asyncio.run(_dub(languages))


async def _dub(languages: list[str]) -> None:
    total_duration = audio_duration(config.audio_file)

    for language in languages:
        with open(f"{language}.srt", "r", encoding="utf-8") as f:
            content = f.read()

        cues, errors = parse_strict(content)
        if errors:
            raise SubtitleValidationError(f"{language}.srt: {'; '.join(errors)}")

        spoken = [(cue, speakable_text(cue.text)) for cue in cues]
        spoken = [(cue, text) for cue, text in spoken if text]
        if not spoken:
            warning(f"{language}.srt has no speakable text; skipping dub")
            continue

        info(f"Dubbing {get_language_name(language)} ({len(spoken)} cues)...")
        await _dub_language(language, spoken, total_duration)


async def _dub_language(
    language: str,
    spoken: list[tuple[Cue, str]],
    total_duration: float | None,
) -> None:
    provider = get_provider()
    language_name = get_language_name(language)
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

    with Progress() as progress:
        progress_task = progress.add_task(f"Dub {language}", total=len(spoken))

        async def speak_cue(text: str) -> bytes:
            async with semaphore:
                audio = await _speak_with_retry(provider, text, language_name)
            progress.update(progress_task, advance=1)
            return audio

        wavs = await asyncio.gather(*(speak_cue(text) for _, text in spoken))

    starts = [cue.start for cue, _ in spoken]
    slots = cue_slots(starts, total_duration)

    with tempfile.TemporaryDirectory() as tmpdir:
        segments = [
            _fit_segment(wav, slot, tmpdir, index)
            for index, (wav, slot) in enumerate(zip(wavs, slots))
        ]
        durations = [len(frames) / (SAMPLE_RATE * SAMPLE_WIDTH * CHANNELS) for frames in segments]
        gaps, final_pad = plan_gaps(starts, durations, total_duration)

        track = io.BytesIO()
        with wave.open(track, "wb") as out:
            out.setnchannels(CHANNELS)
            out.setsampwidth(SAMPLE_WIDTH)
            out.setframerate(SAMPLE_RATE)
            for gap, frames in zip(gaps, segments):
                out.writeframes(_silence(gap))
                out.writeframes(frames)
            out.writeframes(_silence(final_pad))

        wav_path = os.path.join(tmpdir, "track.wav")
        with open(wav_path, "wb") as f:
            f.write(track.getvalue())
        _encode_mp3(wav_path, f"{language}.mp3")

    info(f"Wrote {language}.mp3")


async def _speak_with_retry(provider, text: str, language_name: str) -> bytes:
    last_error: Exception | None = None
    for attempt in range(max(1, config.retry)):
        try:
            return await provider.speak(text, language_name)
        except Exception as e:
            last_error = e
            if attempt < config.retry - 1:
                await asyncio.sleep(backoff(attempt))
    raise RuntimeError(f"Text-to-speech failed for {text[:40]!r}: {last_error}")


def speakable_text(text: str) -> str:
    """
    The part of a cue worth speaking: sound effects and stage directions are not.
    """
    return " ".join(BRACKETED.sub(" ", text).split())


def cue_slots(starts: list[float], total_duration: float | None) -> list[float | None]:
    """
    How long each cue may speak: until the next cue starts, or the audio ends.

    The last slot is None when the audio length is unknown; unlimited speech
    there is better than guessing a limit.
    """
    slots: list[float | None] = []
    for index, start in enumerate(starts):
        if index + 1 < len(starts):
            slots.append(max(0.0, starts[index + 1] - start))
        elif total_duration is not None:
            slots.append(max(0.0, total_duration - start))
        else:
            slots.append(None)
    return slots


def plan_gaps(
    starts: list[float],
    durations: list[float],
    total_duration: float | None,
) -> tuple[list[float], float]:
    """
    Return the silence to insert before each segment, and after the last one.

    Segments are placed at their cue's start time unless earlier speech is
    still running, in which case they follow it immediately.
    """
    gaps: list[float] = []
    cursor = 0.0
    for start, duration in zip(starts, durations):
        gap = max(0.0, start - cursor)
        gaps.append(gap)
        cursor += gap + duration
    final_pad = max(0.0, total_duration - cursor) if total_duration is not None else 0.0
    return gaps, final_pad


def atempo_filter(ratio: float) -> str | None:
    """
    An ffmpeg atempo chain for the given speed-up, or None when none is needed.

    A single atempo only accepts factors up to 2.0, so larger ratios are split
    into a chain.
    """
    if ratio <= 1.02:
        return None
    parts = []
    while ratio > 2.0:
        parts.append(2.0)
        ratio /= 2.0
    parts.append(ratio)
    return ",".join(f"atempo={part:.5f}" for part in parts)


def _fit_segment(wav_bytes: bytes, slot: float | None, tmpdir: str, index: int) -> bytes:
    """
    Return the segment as canonical PCM frames, sped up to fit its slot.
    """
    frames = _normalized_frames(wav_bytes, tmpdir, index)
    duration = len(frames) / (SAMPLE_RATE * SAMPLE_WIDTH * CHANNELS)

    if slot and slot > 0 and duration > slot:
        filter_chain = atempo_filter(min(duration / slot, MAX_TEMPO))
        if filter_chain:
            frames = _apply_filter(frames, filter_chain, tmpdir, index)
    return frames


def _normalized_frames(wav_bytes: bytes, tmpdir: str, index: int) -> bytes:
    """
    Return raw PCM frames at the canonical rate, resampling only when needed.
    """
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
            if (
                wav.getframerate() == SAMPLE_RATE
                and wav.getnchannels() == CHANNELS
                and wav.getsampwidth() == SAMPLE_WIDTH
            ):
                return wav.readframes(wav.getnframes())
    except wave.Error:
        pass

    source = os.path.join(tmpdir, f"raw_{index}")
    with open(source, "wb") as f:
        f.write(wav_bytes)
    return _run_ffmpeg_to_frames(["-i", source], tmpdir, index)


def _apply_filter(frames: bytes, filter_chain: str, tmpdir: str, index: int) -> bytes:
    source = os.path.join(tmpdir, f"fit_{index}.wav")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(CHANNELS)
        wav.setsampwidth(SAMPLE_WIDTH)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(frames)
    with open(source, "wb") as f:
        f.write(buffer.getvalue())
    return _run_ffmpeg_to_frames(["-i", source, "-filter:a", filter_chain], tmpdir, index)


def _run_ffmpeg_to_frames(input_args: list[str], tmpdir: str, index: int) -> bytes:
    output = os.path.join(tmpdir, f"norm_{index}.wav")
    cmd = [
        "ffmpeg", "-y", *input_args,
        "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS), "-c:a", "pcm_s16le",
        output,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        stderr = e.stderr.decode() if getattr(e, "stderr", None) else str(e)
        raise RuntimeError(f"ffmpeg failed while preparing a dub segment: {stderr}")
    with wave.open(output, "rb") as wav:
        return wav.readframes(wav.getnframes())


def _silence(seconds: float) -> bytes:
    return b"\x00" * (int(round(seconds * SAMPLE_RATE)) * SAMPLE_WIDTH * CHANNELS)


def _encode_mp3(wav_path: str, mp3_path: str) -> None:
    cmd = ["ffmpeg", "-y", "-i", wav_path, "-c:a", "libmp3lame", "-q:a", "4", mp3_path]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        stderr = e.stderr.decode() if getattr(e, "stderr", None) else str(e)
        raise RuntimeError(f"Failed to encode {mp3_path}: {stderr}")
