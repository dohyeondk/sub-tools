import re

from typing import Union
from google import genai
from google.genai import types
from google.genai.errors import ClientError

class RateLimitExceededError(Exception):
    """
    Custom exception for rate limit exceeded errors.
    """
    pass


async def upload_file(api_key: str, path: str) -> types.File:
    """
    Uploads a file to the Google GenAI API.
    """
    client = genai.Client(api_key=api_key)
    return await client.aio.files.upload(path=path)


async def delete_file(api_key: str, file: types.File) -> types.DeleteFileResponse:
    """
    Deletes a file from the Google GenAI API.
    """
    client = genai.Client(api_key=api_key)
    return await client.aio.files.delete(name=file.name)


async def audio_to_subtitles(
    api_key: str,
    file: types.File,
    audio_format: str,
    language: str,
) -> Union[str, None]:
    """
    Converts an audio file to subtitles.
    """
    client = genai.Client(api_key=api_key)

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
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash-thinking-exp-1219",
            contents=[
                types.Part.from_uri(file_uri=file.uri, mime_type=f"audio/{audio_format}"),
            ],
            config=types.GenerateContentConfig(
                system_instruction=[system_instruction],
                candidate_count=1,
            ),
        )
        text = response.candidates[0].content.parts[-1].text
        text = _remove_unneeded_characters(text)
        text = _fix_invalid_timestamp(text)
        return text
    
    except ClientError as e:
        if e.code == 429:
            raise RateLimitExceededError
        print(f"Error: {str(e)}")
        return None

    except Exception as e:
        print(f"Error: {str(e)}")
        return None


def _remove_unneeded_characters(text: str) -> str:
    return text.strip().strip("```").strip("srt")


def _fix_invalid_timestamp(text: str) -> str:
    pattern = re.compile(r"^(\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2},\d{3})$", flags=re.MULTILINE)
    return pattern.sub(r"00:\1 --> 00:\2", text)
