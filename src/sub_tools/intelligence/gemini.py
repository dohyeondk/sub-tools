import asyncio
import re
from typing import Optional, Union

from google import genai
from google.api_core import exceptions as google_exceptions
from google.genai import types

from ..config import config


async def proofread_srt_with_gemini(
    audio_path: str,
    audio_format: str,
    srt_content: str,
) -> Union[str, None]:
    """
    Proofread an SRT file using Gemini with audio as reference.

    Args:
        audio_path: Path to the audio file
        audio_format: Audio file format (mp3, wav, etc.)
        srt_content: Content of the SRT file to proofread

    Returns:
        Proofread SRT content, or None if proofreading failed
    """
    system_instruction = """
    You are a professional transcription proofreader.
    You will receive an English SRT subtitle file and the corresponding audio file.

    Your task is to:
    1. Listen to the audio carefully
    2. Compare it with the provided SRT transcription
    3. Fix any transcription errors, mistakes, or inaccuracies
    4. Maintain the exact same timing (timestamps) as the input SRT
    5. Improve punctuation and capitalization if needed
    6. Clean up filler words ("um", "uh", "like", "you know") if they appear incorrectly
    7. Fix any misheard words or phrases

    CRITICAL REQUIREMENTS:
    1. Output ONLY the corrected SRT file. No code blocks, no explanations.
    2. Keep ALL timestamps exactly as they are in the input SRT
    3. Preserve the SRT format perfectly (number, timestamp, text, blank line)
    4. Only modify the text content, not the structure or timing
    5. The output must be valid SRT format

    Return the proofread SRT file.
    """

    return await _call_gemini_api(
        system_instruction=system_instruction,
        audio_path=audio_path,
        audio_format=audio_format,
        text_input=f"SRT to proofread:\n\n{srt_content}",
    )


async def translate_srt_with_gemini(
    audio_path: str,
    audio_format: str,
    srt_content: str,
    target_language: str,
) -> Union[str, None]:
    """
    Translate an English SRT file to target language using Gemini with audio as reference.

    Args:
        audio_path: Path to the audio file
        audio_format: Audio file format (mp3, wav, etc.)
        srt_content: Content of the English SRT file to translate
        target_language: Target language name (e.g., "Spanish", "French")

    Returns:
        Translated SRT content, or None if translation failed
    """
    system_instruction = f"""
    You are a professional translator specializing in subtitle translation.
    You will receive an English SRT subtitle file and the corresponding audio file.

    Your task is to:
    1. Translate the English subtitles to {target_language}
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
    - Preserve the tone and meaning of the original English
    - Keep proper names in their original form unless they have standard {target_language} equivalents
    - Maintain [sound effects] in brackets
    - Use appropriate punctuation for {target_language}

    Return the translated SRT file in {target_language}.
    """

    return await _call_gemini_api(
        system_instruction=system_instruction,
        audio_path=audio_path,
        audio_format=audio_format,
        text_input=f"English SRT to translate:\n\n{srt_content}",
    )


async def _call_gemini_api(
    system_instruction: str,
    audio_path: Optional[str] = None,
    audio_format: Optional[str] = None,
    text_input: Optional[str] = None,
) -> Optional[str]:
    """
    Helper method to call Gemini API with retries for rate limits.
    """
    client = genai.Client(api_key=config.gemini_api_key)

    # Build parts for the content
    parts = []

    if audio_path and audio_format:
        # Read audio file
        with open(audio_path, "rb") as audio_file:
            audio_data = audio_file.read()

        mime_type_map = {
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "flac": "audio/flac",
            "aac": "audio/aac",
            "ogg": "audio/ogg",
            "opus": "audio/opus",
        }
        mime_type = mime_type_map.get(audio_format.lower(), f"audio/{audio_format}")
        parts.append(types.Part.from_bytes(data=audio_data, mime_type=mime_type))

    if text_input:
        parts.append(types.Part.from_text(text=text_input))

    # Create content with proper structure
    contents = [
        types.Content(
            role="user",
            parts=parts,
        ),
    ]

    # Create generation config with system instruction
    generate_content_config = types.GenerateContentConfig(
        system_instruction=[
            types.Part.from_text(text=system_instruction),
        ],
    )

    for attempt in range(config.gemini_max_retries):
        try:
            response = await client.aio.models.generate_content(
                model=config.gemini_model,
                contents=contents,
                config=generate_content_config,
            )
            text = response.text
            text = _remove_unneeded_characters(text)
            text = _fix_invalid_timestamp(text)
            return text

        except google_exceptions.ResourceExhausted as e:
            if attempt < config.gemini_max_retries - 1:
                wait_time = 2**attempt  # Exponential backoff: 1, 2, 4 seconds
                await asyncio.sleep(wait_time)
                continue
            else:
                raise e
        except Exception:
            return None
    return None


def _remove_unneeded_characters(text: Union[str, None]) -> str:
    """Remove common wrappers like code fences and stray language tags without altering SRT content."""
    if text is None:
        return ""

    cleaned = text.strip()

    # Remove leading code fence with optional language (e.g., ```srt or ```SRT)
    cleaned = re.sub(r"^```\s*[a-zA-Z0-9_-]*\s*\n", "", cleaned, count=1)
    # Remove trailing code fence
    cleaned = re.sub(r"\n?```\s*$", "", cleaned, count=1)

    # Remove a bare leading language tag without fences (e.g., 'srt' or 'SRT')
    cleaned = re.sub(r"^(?:srt|SRT)\s*\n", "", cleaned, count=1)

    return cleaned.strip()


def _fix_invalid_timestamp(text: str) -> str:
    pattern = re.compile(
        r"^(\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2},\d{3})$", flags=re.MULTILINE
    )
    return pattern.sub(r"00:\1 --> 00:\2", text)
