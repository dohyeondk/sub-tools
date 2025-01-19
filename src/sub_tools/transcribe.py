import asyncio

from dataclasses import dataclass
from .intelligence.client import audio_to_subtitles, upload_file, delete_file, RateLimitExceededError
from .media.info import get_duration
from .subtitles.serializer import serialize_subtitles
from .subtitles.validator import validate_subtitles, SubtitleValidationError
from .system.directory import paths_with_offsets
from .system.language import get_language_name
from .system.logger import write_log


max_concurrent_tasks = 4
semaphore = asyncio.Semaphore(max_concurrent_tasks)


@dataclass
class TranscribeConfig:
    directory: str = "tmp"
    sleep_for_rate_limit: int = 60


def transcribe(parsed, config: TranscribeConfig = TranscribeConfig()) -> None:
    print("Transcribing...")
    asyncio.run(_transcribe(parsed, config))


async def _transcribe(parsed, config: TranscribeConfig) -> None:
    tasks = []

    for path, offset in paths_with_offsets(parsed.audio_segment_prefix, parsed.audio_segment_format, f"./{config.directory}"):
        for language_code in parsed.languages:
            task = asyncio.create_task(
                _transcribe_item(
                    path,
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


async def _transcribe_item(
    audio_segment_path: str,
    audio_segment_format: str,
    offset: int,
    language_code: str,
    api_key: str,
    retry: int,
    debug: bool,
    config: TranscribeConfig,
) -> None:
    async with semaphore:
        language = get_language_name(language_code)
        file = None

        try:
            file_path = f"{config.directory}/{audio_segment_path}"
            file = await upload_file(api_key, file_path)
            duration_ms = get_duration(file_path) * 1000

            for attempt in range(retry):
                print(f"Transcribe attempt {attempt + 1}/{retry} for audio at {offset} to {language}")

                try:
                    subtitles = await audio_to_subtitles(api_key, file, audio_segment_format, language)
                except Exception as e:
                    if debug:
                        write_log(f"{language_code}_{offset}", "API Error", e, language, offset, directory=f"./{config.directory}")
                    await asyncio.sleep(config.sleep_for_rate_limit)
                    continue

                try:
                    validate_subtitles(subtitles, duration_ms)
                    if debug:
                        write_log(f"{language_code}_{offset}", "Valid", language, offset, subtitles, directory=f"./{config.directory}")
                    serialize_subtitles(subtitles, language_code, int(offset), config.directory)
                    break # Happy path
                except Exception as e:
                    if debug:
                        write_log(f"{language_code}_{offset}", "Invalid", e, language, offset, subtitles or "no subtitles", directory=f"./{config.directory}")
                    await asyncio.sleep(min(2**attempt, 60))

        except Exception as e:
            if debug:
                print(f"Error: {str(e)}")

        finally:
            await delete_file(api_key, file)
