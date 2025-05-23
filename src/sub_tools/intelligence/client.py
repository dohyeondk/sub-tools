import re
import base64
from typing import Union
from openai import AsyncOpenAI, RateLimitError


class TranscriptionError(Exception):
    """
    Base exception for transcription-related errors.
    """
    pass


class RateLimitExceededError(TranscriptionError):
    """
    Custom exception for rate limit exceeded errors.
    """
    pass


class AudioProcessingError(TranscriptionError):
    """
    Exception raised when there's an error processing the audio file.
    """
    pass


class APIConnectionError(TranscriptionError):
    """
    Exception raised when there's an error connecting to the API.
    """
    pass


class InvalidResponseError(TranscriptionError):
    """
    Exception raised when the API response is invalid or cannot be parsed.
    """
    pass


async def audio_to_subtitles(
    api_key: str,
    model: str,
    audio_path: str,
    audio_format: str,
    language: str,
) -> str:
    """
    Converts an audio file to subtitles.

    Args:
        api_key: Gemini API key
        model: Model name to use for transcription
        audio_path: Path to the audio file
        audio_format: Format of the audio file (e.g., mp3, wav)
        language: Target language for transcription

    Returns:
        String containing SRT formatted subtitles

    Raises:
        AudioProcessingError: When there's an error processing the audio file
        RateLimitExceededError: When API rate limits are exceeded
        APIConnectionError: When there's an error connecting to the API
        InvalidResponseError: When the API response is invalid or cannot be processed
        TranscriptionError: For other transcription-related errors
    """
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    system_instruction = f"""
    You're a professional transcriber and translator working specifically with {language} as the target language. 
    You take an audio file and MUST output the transcription in {language}.
    You will return an accurate, high-quality SubRip Subtitle (SRT) file.
    
    CRITICAL REQUIREMENTS:
    1. IMPORTANT: Output must be only the SRT in {language}. Do not use code blocks or any other formatting.
    2. All timestamps must be in 00:00:00,000 --> 00:00:00,000 format (hh:mm:ss,ms). No deviation is allowed.
    3. Each segment should be 1-2 lines and maximum 5 seconds. Refer to the example SRT file for reference in terms of the size of the segments.
       - Do not just decrease the end timestamp to fit within 5 seconds without splitting the text.
       - When needed, split a sentence into multiple segments, and make sure the timestamps are correct.
    4. Every subtitle entry MUST have:
       - A sequential number
       - A timestamp line
       - 1-2 lines of text
       - A blank line between entries.
    5. The SRT file MUST cover the entire input audio file without missing any content.
    6. The SRT file MUST be in the target language.
    7. Before returning the final SRT, re-check that:
       - All lines follow the SRT numbering and timestamp format strictly.
       - There are no overlaps, and each timestamp is valid and sequential.
       - There are no extraneous characters or missing commas for the timestamps.
    
    Timing Guidelines:
    - Ensure no timestamp overlaps.
    - Always use full timestamp format (hh:mm:ss,ms).
    - Ensure the timing aligns closely with the spoken words for synchronization. 
    - Make sure the subtitles cover the entire audio file.

    Text Guidelines:
    - Use proper punctuation and capitalization.
    - Keep original meaning but clean up filler words like "um", "uh", "like", "you know", etc.
    - Clean up stutters like "I I I" or "uh uh uh".
    - Replace profanity with mild alternatives.
    - Include [sound effects] in brackets if applicable.

    EXAMPLE SRT FILE:

    1
    00:00:00,000 --> 00:00:04,620
    (congregation applauds)
    So change is hard.
    
    2
    00:00:04,620 --> 00:00:06,120
    We're coming out of the holidays,
    
    3
    00:00:06,120 --> 00:00:07,440
    the decorations are going up,
    
    4
    00:00:07,440 --> 00:00:09,240
    we're stepping into a new year.
    
    5
    00:00:09,240 --> 00:00:10,890
    And so a lot of us are thinking about,
    
    6
    00:00:10,890 --> 00:00:14,943
    hey, what would I like to be different in my life in 2025?
    """

    try:
        with open(audio_path, "rb") as audio_file:
            base64_audio = base64.b64encode(audio_file.read()).decode('utf-8')
    except Exception as e:
        raise AudioProcessingError(f"Failed to read audio file {audio_path}: {str(e)}")

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": system_instruction
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": base64_audio,
                                "format": audio_format
                            }
                        }
                    ]
                }
            ]
        )
        text = response.choices[0].message.content
        text = _remove_unneeded_characters(text)
        text = _fix_invalid_timestamp(text)
        return text
    
    except RateLimitError:
        raise RateLimitExceededError(f"API rate limit exceeded when transcribing {audio_path}")
    except Exception as e:
        # More specific error handling based on error type
        error_message = str(e).lower()
        if "connection" in error_message or "timeout" in error_message:
            raise APIConnectionError(f"Failed to connect to API when transcribing {audio_path}: {str(e)}")
        elif "invalid" in error_message or "parse" in error_message or "format" in error_message:
            raise InvalidResponseError(f"Invalid response from API when transcribing {audio_path}: {str(e)}")
        else:
            raise TranscriptionError(f"Unexpected error when transcribing {audio_path}: {str(e)}")


def _remove_unneeded_characters(text: str) -> str:
    return text.strip().strip("```").strip("srt")


def _fix_invalid_timestamp(text: str) -> str:
    pattern = re.compile(r"^(\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2},\d{3})$", flags=re.MULTILINE)
    return pattern.sub(r"00:\1 --> 00:\2", text)
