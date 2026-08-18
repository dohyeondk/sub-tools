"""
Provider-agnostic transcription and translation.

The prompts, the repair/validate loop, and the retry policy live here; the
provider modules only know how to answer one request. The provider is selected
explicitly in config, with model-name inference retained for compatibility.
"""

import asyncio
from types import ModuleType
from typing import Callable, Optional

from rich.progress import Progress

from sub_tools.system.console import info, warning
from sub_tools.system.file import should_skip
from sub_tools.system.language import get_language_name

from ..config import config
from ..media.converter import audio_duration
from ..subtitles.repair import repair_subtitles
from ..subtitles.validator import SubtitleValidationError, find_problems


def get_provider() -> ModuleType:
    """
    Return the configured provider module.
    """
    provider_name = config.resolved_provider

    if provider_name == "openai":
        from . import openai

        return openai
    if provider_name == "openrouter":
        from . import openrouter

        return openrouter
    if provider_name == "anthropic":
        from . import anthropic

        return anthropic
    if provider_name in ("google", "gemini"):
        from . import gemini

        return gemini

    raise ValueError(f"Unsupported provider: {provider_name}")


def transcribe() -> None:
    """
    Transcribe the audio into subtitles using the configured model.
    """
    if should_skip(f"{config.source_language}.srt"):
        return

    asyncio.run(_transcribe())


async def _transcribe() -> None:
    provider = get_provider()
    if not getattr(provider, "can_transcribe_audio", lambda: True)():
        raise RuntimeError(
            "The Anthropic API does not accept audio input. Use an audio-capable "
            "provider/model for transcribe, or run Anthropic for translate with an "
            "existing source SRT."
        )

    info(f"Transcribing with {config.model}...")

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
    1. Output ONLY the subtitles as plain SRT text. No code blocks, no JSON, no explanations.
    2. Preserve the SRT format perfectly (number, timestamp, text, blank line)
    3. Every timestamp must be HH:MM:SS,mmm --> HH:MM:SS,mmm, always including the
       hours field, even after the first hour of audio
    4. Cover the entire recording from beginning to end, including the final minutes
    5. Use correct punctuation and capitalization
    6. The output must be valid SRT format

    Reply with the SRT text now.
    """

    provider.prepare_audio()
    await _generate_subtitles(
        output_file=f"{language_code}.srt",
        system_instruction=system_instruction,
        text=f"Transcribe this {language} audio into an SRT subtitle file.",
    )


def translate() -> None:
    """
    Translate the source subtitles into each target language using the configured model.
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

    info(f"Translating with {config.model}...")

    tasks = []

    with Progress() as progress:
        progress_task = progress.add_task("Translation", total=len(target_language_codes))

        # Prepare the audio once, before the concurrent tasks race to do it.
        # Text-only models translate without hearing the recording.
        provider = get_provider()
        if provider.accepts_audio():
            provider.prepare_audio()

        for language_code in target_language_codes:
            task = asyncio.create_task(
                _translate_language(
                    srt_content=srt_content,
                    source_language_code=source_language_code,
                    target_language_code=language_code,
                    completion=lambda: progress.update(progress_task, advance=1),
                )
            )
            tasks.append(task)

        await asyncio.gather(*tasks)


async def _translate_language(
    srt_content: str,
    source_language_code: str,
    target_language_code: str,
    completion: Callable[[], None],
) -> None:
    source_language = get_language_name(source_language_code)
    target_language = get_language_name(target_language_code)

    # Text-only models translate from the SRT alone; audio-capable models also
    # get the recording for context and tone.
    with_audio = get_provider().accepts_audio()
    received = (
        f"an {source_language} SRT subtitle file and the corresponding audio file"
        if with_audio
        else f"an {source_language} SRT subtitle file"
    )
    context_step = (
        "2. Listen to the audio to understand context and tone"
        if with_audio
        else "2. Use the surrounding subtitles to understand context and tone"
    )

    system_instruction = f"""
    You are a professional translator specializing in subtitle translation.
    You will receive {received}.

    Your task is to:
    1. Translate the {source_language} subtitles to {target_language}
    {context_step}
    3. Keep the exact same timing (timestamps) as the input SRT
    4. Ensure translations are natural and culturally appropriate for {target_language}

    CRITICAL REQUIREMENTS:
    1. Output ONLY the translated subtitles as plain SRT text in {target_language}. No code blocks, no JSON, no explanations.
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

    Reply with the translated SRT text in {target_language} now.
    """

    await _generate_subtitles(
        output_file=f"{target_language_code}.srt",
        system_instruction=system_instruction,
        text=f"{source_language} SRT to translate:\n\n{srt_content}",
        reference=srt_content,
        with_audio=with_audio,
    )
    completion()


async def _generate_subtitles(
    output_file: str,
    system_instruction: str,
    text: Optional[str] = None,
    reference: Optional[str] = None,
    with_audio: bool = True,
) -> None:
    """
    Ask the model for subtitles, repairing and checking the answer before accepting it.

    Models get the words right far more reliably than the container, so a reply
    that fails to parse is repaired first and only re-requested if the repair
    cannot save it.
    """
    provider = get_provider()
    duration = audio_duration(config.audio_file)
    attempts = max(1, config.retry)
    last_errors: list[str] = []

    for attempt in range(attempts):
        content = await provider.generate(
            system_instruction=system_instruction,
            text=text,
            with_audio=with_audio,
        )

        if config.debug:
            with open(f"{output_file}.attempt{attempt + 1}.raw", "w", encoding="utf-8") as f:
                f.write(content or "")

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
