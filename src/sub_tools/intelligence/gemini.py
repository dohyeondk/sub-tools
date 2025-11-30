import asyncio
from typing import Callable, Optional

from google import genai
from google.api_core import exceptions as google_exceptions
from google.genai import types
from rich.progress import Progress

from sub_tools.system.console import info
from sub_tools.system.file import should_skip
from sub_tools.system.language import get_language_name

from ..config import config


def proofread() -> None:
    """Proofread the source SRT file with Gemini."""

    if should_skip(f"{config.source_language}.srt"):
        return

    asyncio.run(_proofread())


async def _proofread() -> None:
    info("Proofreading with Gemini...")

    language_code = config.source_language
    language = get_language_name(language_code)

    srt_file = config.srt_file
    with open(srt_file, "r", encoding="utf-8") as f:
        srt_content = f.read()

    system_instruction = f"""
    You are a professional transcription proofreader.
    You will receive an {language} SRT subtitle file and the corresponding audio file.

    Your task is to:
    1. Listen to the audio carefully
    2. Compare it with the provided SRT transcription
    3. Fix any obvious transcription errors, mistakes, or inaccuracies
    4. Keep timestamps accurate - maintain exact timing as in the input SRT
    5. Improve punctuation and capitalization if needed
    6. Clean up filler words ("um", "uh", "like", "you know") if they appear incorrectly
    7. Fix any misheard words or phrases
    8. Split long segments to ensure readability - no more than 2 lines visible at a time (max ~80 characters per line)

    CRITICAL REQUIREMENTS:
    1. Output ONLY the corrected SRT file. No code blocks, no explanations.
    2. Keep ALL timestamps exactly as they are in the input SRT
    3. If a segment is too long, you may split it into multiple segments with appropriate timing
    4. Ensure no subtitle block exceeds 2 lines of text (~80 characters per line max)
    5. Preserve the SRT format perfectly (number, timestamp, text, blank line)
    6. Only modify the text content and split long segments when necessary
    7. The output must be valid SRT format

    Return the proofread SRT file.
    """

    file = _upload_file(config.audio_file)
    await _call_gemini_api(
        output_file=f"{language_code}.srt",
        system_instruction=system_instruction,
        file=file,
        text=f"SRT to proofread:\n\n{srt_content}",
    )


def translate() -> None:
    """Translate the source SRT file with Gemini."""

    asyncio.run(_translate())


async def _translate() -> None:
    language_code = config.source_language

    srt_file = f"{language_code}.srt"
    with open(srt_file, "r", encoding="utf-8") as f:
        srt_content = f.read()

    # Filter out source language from target languages
    target_language_codes = [
        lang
        for lang in config.languages
        if lang != language_code and not should_skip(f"{lang}.srt")
    ]

    if not target_language_codes:
        return

    info("Translating with Gemini...")

    tasks = []

    with Progress() as progress:
        progress_task = progress.add_task(
            "Translation", total=len(target_language_codes)
        )

        file = _upload_file(config.audio_file)

        for language_code in target_language_codes:
            if should_skip(f"{language_code}.srt"):
                continue

            task = asyncio.create_task(
                _translate_language(
                    file=file,
                    srt_content=srt_content,
                    source_language_code=config.source_language,
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
    3. Maintain the exact same timing (timestamps) as the input SRT
    4. Ensure translations are natural and culturally appropriate for {target_language}
    5. Keep the translation synchronized with the speech timing

    CRITICAL REQUIREMENTS:
    1. Output ONLY the translated SRT file in {target_language}. No code blocks, no explanations.
    2. Keep ALL timestamps exactly as they are in the input SRT
    3. Preserve the SRT format perfectly (number, timestamp, text, blank line)
    4. Only translate the text content, not the structure or timing
    5. The output must be valid SRT format
    6. All subtitle text must be in {target_language}

    Translation Guidelines:
    - Use natural, conversational {target_language}
    - Preserve the tone and meaning of the original {source_language}
    - Keep proper names in their original form unless they have standard {target_language} equivalents
    - Maintain [sound effects] in brackets
    - Use appropriate punctuation for {target_language}

    Return the translated SRT file in {target_language}.
    """

    await _call_gemini_api(
        output_file=f"{target_language_code}.srt",
        system_instruction=system_instruction,
        file=file,
        text=f"{source_language} SRT to translate:\n\n{srt_content}",
    )
    completion()


async def _call_gemini_api(
    output_file: str,
    system_instruction: str,
    file: Optional[types.File] = None,
    text: Optional[str] = None,
) -> None:
    """
    Helper method to call Gemini API with retries for rate limits.
    """
    client = genai.Client(api_key=config.gemini_api_key)

    # Build parts for the content
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
                        include_thoughts=True, thinking_level=types.ThinkingLevel.HIGH
                    ),
                    tools=tools,
                ),
            )
            text = response.text
            if text:
                with open(output_file, "w") as f:
                    f.write(text)
                return

        except google_exceptions.ResourceExhausted as e:
            if attempt < config.retry - 1:
                wait_time = 2**attempt  # Exponential backoff: 1, 2, 4 seconds
                await asyncio.sleep(wait_time)
                continue
            else:
                raise e
        except Exception as e:
            raise e


def _upload_file(file_path: str) -> types.File:
    client = genai.Client(api_key=config.gemini_api_key)
    file = client.files.upload(file=file_path)
    return file
