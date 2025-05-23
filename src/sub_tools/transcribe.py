import asyncio
from dataclasses import dataclass
from argparse import Namespace
from typing import List, Coroutine, Any
from rich.progress import Progress

from .intelligence.client import audio_to_subtitles, RateLimitExceededError
from .media.info import get_duration
from .subtitles.serializer import serialize_subtitles
from .subtitles.validator import validate_subtitles, SubtitleValidationError
from .system.directory import paths_with_offsets
from .system.language import get_language_name
from .system.logger import write_log
from .system.rate_limiter import RateLimiter
from .system.console import info, error

model = 'gemini-2.5-flash-preview-04-17'
rate_limit = 10

rate_limiter = RateLimiter(rate_limit=rate_limit, period=60)


@dataclass
class TranscribeConfig:
    directory: str = "tmp"


def transcribe(parsed: Namespace, config: TranscribeConfig = TranscribeConfig()) -> None:
    asyncio.run(_transcribe(parsed, config))


async def _transcribe(parsed: Namespace, config: TranscribeConfig) -> None:
    info("Transcribing files...")
    tasks: List[asyncio.Task] = []

    with Progress() as progress:
        for language_code in parsed.languages:
            language_name = get_language_name(language_code)
            path_offset_list = paths_with_offsets(parsed.audio_segment_prefix, parsed.audio_segment_format, f"./{config.directory}")

            progress_task = progress.add_task(language_name, total=len(path_offset_list))

            for path, offset in path_offset_list:
                async def run(
                    path: str,
                    offset: int,
                    language_code: str,
                    progress_task: int
                ) -> None:
                    audio_path = f"./{config.directory}/{path}"
                    duration_ms = get_duration(audio_path) * 1000
                    await _transcribe_item(
                        audio_path,
                        int(duration_ms),
                        parsed.audio_segment_format,
                        offset,
                        language_code,
                        parsed.gemini_api_key,
                        parsed.retry,
                        parsed.debug,
                        config,
                    )
                    progress.update(progress_task, advance=1)
                task = asyncio.create_task(run(path, offset, language_code, progress_task))
                tasks.append(task)

        await asyncio.gather(*tasks)


async def _transcribe_item(
    audio_path: str,
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

            try:
                subtitles = await audio_to_subtitles(api_key, model, audio_path, audio_segment_format, language)

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
            except Exception as e:
                if debug:
                    write_log(f"{language_code}_{offset}", "Unexpected Error", f"Exception: {e}", language, offset, directory=f"./{config.directory}")

            # Use consistent backoff strategy
            wait_time = min(2**attempt, 60)
            await asyncio.sleep(wait_time)

    except Exception as e:
        if debug:
            error(f"Error in transcription process: {str(e)}")
