import asyncio
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
from ..subtitles.validator import SubtitleValidationError, find_problems


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
