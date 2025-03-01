import asyncio
from dataclasses import dataclass
from google.genai import types
from google.genai.errors import ClientError

from .intelligence.client import audio_to_subtitles, upload_file, delete_file, RateLimitExceededError
from .media.info import get_duration
from .subtitles.serializer import serialize_subtitles
from .subtitles.validator import validate_subtitles, SubtitleValidationError
from .system.directory import paths_with_offsets
from .system.language import get_language_name
from .system.logger import write_log
from .system.rate_limiter import RateLimiter


rate_limiter = RateLimiter(rate_limit=10, period=60)


@dataclass
class TranscribeConfig:
    directory: str = "tmp"


def transcribe(parsed, config: TranscribeConfig = TranscribeConfig()) -> None:
    print("Transcribing...")
    asyncio.run(_transcribe(parsed, config))


async def _transcribe(parsed, config: TranscribeConfig) -> None:
    tasks = []
    files = []

    for path, offset in paths_with_offsets(parsed.audio_segment_prefix, parsed.audio_segment_format, f"./{config.directory}"):
        file_path = f"{config.directory}/{path}"
        print(f"Upload file: {file_path}")
        file = await upload_file(parsed.gemini_api_key, file_path)
        files.append(file)
        duration_ms = get_duration(file_path) * 1000

        for language_code in parsed.languages:
            task = asyncio.create_task(
                _transcribe_item(
                    file,
                    duration_ms,
                    parsed.audio_segment_format,
                    offset,
                    language_code,
                    parsed.gemini_api_key,
                    parsed.retry,
                    parsed.debug,
                    config,
                )
            )
            tasks.append(task)

    await asyncio.gather(*tasks)

    for file in files:
        try:
            await delete_file(parsed.gemini_api_key, file)
        except Exception as e:
            if parsed.debug:
                print(f"Failed to delete file: {str(e)}")


async def _transcribe_item(
    file: types.File,
    duration_ms: int,
    audio_segment_format: str,
    offset: int,
    language_code: str,
    api_key: str,
    retry: int,
    debug: bool,
    config: TranscribeConfig,
) -> None:
    language = get_language_name(language_code)

    try:
        for attempt in range(retry):
            # Apply rate limiting for the audio_to_subtitles call
            await rate_limiter.acquire()
            print(f"Transcribe attempt {attempt + 1}/{retry} for audio at {offset} to {language}")

            try:
                subtitles = await audio_to_subtitles(api_key, file, audio_segment_format, language)

                try:
                    validate_subtitles(subtitles, duration_ms)

                    if debug:
                        write_log(f"{language_code}_{offset}", "Valid", language, offset, subtitles, directory=f"./{config.directory}")
                    serialize_subtitles(subtitles, language_code, int(offset), config.directory)
                    break  # Happy path

                except SubtitleValidationError as e:
                    if debug:
                        write_log(f"{language_code}_{offset}", "Invalid", e, language, offset, subtitles, directory=f"./{config.directory}")

                    # Use consistent backoff strategy
                    wait_time = min(2**attempt, 60)
                    await asyncio.sleep(wait_time)

            except RateLimitExceededError:
                if debug:
                    write_log(f"{language_code}_{offset}", "Rate Limit Exceeded", "API rate limit exceeded", language, offset, directory=f"./{config.directory}")
            except ClientError as e:
                if debug:
                    write_log(f"{language_code}_{offset}", "API Error", f"ClientError: {e}", language, offset, directory=f"./{config.directory}")
            except Exception as e:
                if debug:
                    write_log(f"{language_code}_{offset}", "Unexpected Error", f"Exception: {e}", language, offset, directory=f"./{config.directory}")

            # Use consistent backoff strategy
            wait_time = min(2**attempt, 60)
            await asyncio.sleep(wait_time)

    except Exception as e:
        if debug:
            print(f"Error in transcription process: {str(e)}")
