"""
New transcription pipeline using WhisperX + Gemini proofreading + Gemini translation.
"""

import asyncio
import os

from rich.progress import Progress

from .config import config
from .intelligence.gemini import proofread_srt_with_gemini, translate_srt_with_gemini
from .intelligence.whisperx import audio_to_srt_with_whisperx
from .system.console import error, info
from .system.language import get_language_name


def transcribe_with_whisperx(parsed) -> str:
    """
    Step 2: Transcribe audio to English SRT using WhisperX.

    Returns:
        Path to the generated English SRT file in temp directory
    """
    info("Transcribing audio with WhisperX...")

    srt_path = audio_to_srt_with_whisperx(
        audio_path=parsed.audio_file,
        output_directory=config.directory or ".",
        device=config.whisperx_device,
        compute_type=config.whisperx_compute_type,
        model_name=config.whisperx_model,
    )

    if not srt_path:
        raise Exception("WhisperX transcription failed")

    return srt_path


def proofread_with_gemini(parsed, srt_path: str) -> str:
    """
    Step 3: Proofread English SRT with Gemini.

    Args:
        srt_path: Path to the WhisperX-generated English SRT

    Returns:
        Path to the proofread English SRT file in output directory
    """
    return asyncio.run(_proofread_with_gemini(parsed, srt_path))


async def _proofread_with_gemini(parsed, srt_path: str) -> str:
    info("Proofreading with Gemini...")

    # Read the WhisperX SRT
    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()

    # Extract audio format from file extension
    audio_format = os.path.splitext(parsed.audio_file)[1][1:]  # Remove the dot

    # Proofread with Gemini
    try:
        proofread_srt = await proofread_srt_with_gemini(
            audio_path=parsed.audio_file,
            audio_format=audio_format,
            srt_content=srt_content,
        )

        if proofread_srt:
            # Save to output directory
            output_path = os.path.join("output", "en.srt")
            if config.output_file:
                # Use custom filename
                base, ext = os.path.splitext(config.output_file)
                output_path = os.path.join("output", f"{base}_en{ext}")

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(proofread_srt)

            return output_path

    except Exception as e:
        if parsed.debug:
            error(f"Error during proofreading: {str(e)}")
        raise Exception(f"Proofreading failed: {str(e)}")


def translate_with_gemini(parsed, english_srt_path: str) -> None:
    """
    Step 4: Translate English SRT to target languages with Gemini.

    Args:
        english_srt_path: Path to the proofread English SRT
    """
    asyncio.run(_translate_with_gemini(parsed, english_srt_path))


async def _translate_with_gemini(parsed, english_srt_path: str) -> None:
    info("Translating to target languages...")

    # Read the proofread English SRT
    with open(english_srt_path, "r", encoding="utf-8") as f:
        english_srt_content = f.read()

    # Filter out English from target languages
    target_languages = [lang for lang in parsed.languages if lang != "en"]

    if not target_languages:
        info("No target languages to translate (only English requested)")
        return

    # Extract audio format from file extension
    audio_format = os.path.splitext(parsed.audio_file)[1][1:]  # Remove the dot

    tasks = []

    with Progress() as progress:
        for language_code in target_languages:
            language_name = get_language_name(language_code)
            progress_task = progress.add_task(language_name, total=1)

            async def translate_language(lang_code, lang_name, prog_task):
                for attempt in range(parsed.retry):
                    try:
                        translated_srt = await translate_srt_with_gemini(
                            audio_path=parsed.audio_file,
                            audio_format=audio_format,
                            srt_content=english_srt_content,
                            target_language=lang_name,
                        )

                        if translated_srt:
                            # Save to output directory
                            output_path = os.path.join("output", f"{lang_code}.srt")
                            if config.output_file:
                                # Use custom filename
                                base, ext = os.path.splitext(config.output_file)
                                output_path = os.path.join(
                                    "output", f"{base}_{lang_code}{ext}"
                                )

                            with open(output_path, "w", encoding="utf-8") as f:
                                f.write(translated_srt)

                            progress.update(prog_task, advance=1)
                            return

                    except Exception as e:
                        if parsed.debug:
                            error(f"Error translating to {lang_name}: {str(e)}")

                    # Exponential backoff
                    wait_time = min(2**attempt, 60)
                    await asyncio.sleep(wait_time)

                error(f"Translation to {lang_name} failed after all retries")

            task = asyncio.create_task(
                translate_language(language_code, language_name, progress_task)
            )
            tasks.append(task)

        await asyncio.gather(*tasks)
