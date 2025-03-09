import yaml
import pysrt
import base64
from typing import Union
from openai import AsyncOpenAI, RateLimitError


class RateLimitExceededError(Exception):
    """
    Custom exception for rate limit exceeded errors.
    """
    pass


async def audio_to_subtitles(
    api_key: str,
    model: str,
    audio_path: str,
    audio_format: str,
    language: str,
) -> Union[str, None]:
    """
    Converts an audio file to subtitles.
    """
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    system_instruction = f"""
    You take an audio file and MUST output the transcription in {language}.
    You will return an accurate, high-quality transcription in YAML format.

    CRITICAL REQUIREMENTS:
    1. IMPORTANT: Output must be only the YAML in {language}. Do not use code blocks or any other formatting.
    2. The YAML file MUST cover the entire input audio file without missing any content.
    3. The YAML file MUST be in the target language.
    4. Before returning the final YAML, re-check that the output is valid YAML.

    Guidelines:
    Timestamps:
        - Ensure the timing aligns closely with the spoken words for synchronization.
        - Make sure the transcription covers the entire audio file.
        - Only use seconds. (61.000 instead of 1:60.000)

    Text:
        - Use proper punctuation and capitalization.
        - Keep original meaning but clean up filler words like "um", "uh", "like", "you know", etc.
        - Clean up stutters like "I I I" or "uh uh uh".
        - Replace profanity with mild alternatives.
        - Include [sound effects] in brackets if applicable.

    EXAMPLE YAML FILE:

    - id: 1
    start_time: 50.000
    end_time: 54.620
    text: "(congregation applauds)\nSo change is hard."
    - id: 2
    start_time: 54.620
    end_time: 56.120
    text: "We're coming out of the holidays,"
    - id: 3
    start_time: 56.120
    end_time: 57.440
    text: "the decorations are going up,"
    - id: 4
    start_time: 57.440
    end_time: 59.240
    text: "we're stepping into a new year."
    - id: 5
    start_time: 59.240
    end_time: 60.890
    text: "And so a lot of us are thinking about,"
    - id: 6
    start_time: 60.890
    end_time: 64.943
    text: "hey, what would I like to be different in my life in 2025?"
    """

    with open(audio_path, "rb") as audio_file:
        base64_audio = base64.b64encode(audio_file.read()).decode('utf-8')

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
        text = _yaml_to_srt(text)
        return text
    
    except RateLimitError as e:
        raise RateLimitExceededError
    except Exception as e:
        return None


def _remove_unneeded_characters(text: str) -> str:
    return text.strip().strip("```").strip("srt").strip("yaml").strip()

def _yaml_to_srt(text: str) -> str:
    """
    Convert YAML data to SRT format.
    """
    yaml_data = yaml.safe_load(text)

    srt = ""

    for item in yaml_data:
        sub = pysrt.SubRipItem(
            index=item['id'],
            start=pysrt.SubRipTime(seconds=item['start_time']),
            end=pysrt.SubRipTime(seconds=item['end_time']),
            text=item['text']
        )
        srt += str(sub) + "\n"

    return srt
