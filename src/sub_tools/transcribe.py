import asyncio

from .intelligence.client import audio_to_subtitles, upload_file, delete_file
from .media.info import get_duration
from .subtitles.serializer import serialize_subtitles
from .subtitles.validator import validate_subtitles, SubtitleValidationError
from .system.directory import paths_with_offsets
from .system.language import get_language_name
from .system.logger import write_log


max_concurrent_tasks = 4
semaphore = asyncio.Semaphore(max_concurrent_tasks)


def transcribe(parsed) -> None:
    print("Transcribing...")
    asyncio.run(__transcribe(parsed))


async def __transcribe(parsed) -> None:
    tasks = []

    for path, offset in paths_with_offsets(parsed.audio_segment_prefix, parsed.audio_segment_format):
        for language_code in parsed.languages:
            task = asyncio.create_task(
                __transcribe_item(
                    path,
                    parsed.audio_segment_format,
                    offset,
                    language_code,
                    parsed.gemini_api_key,
                    parsed.retry
                )
            )
            tasks.append(task)

    await asyncio.gather(*tasks)


async def __transcribe_item(
    audio_segment_path: str,
    audio_segment_format: str,
    offset: int,
    language_code: str,
    api_key: str,
    retry: int
) -> None:
    async with semaphore:
        language = get_language_name(language_code)
        file = None

        try:
            file = await upload_file(api_key, audio_segment_path)
            duration_ms = get_duration(audio_segment_path) * 1000

            for attempt in range(retry):
                print(f"Transcribe attempt {attempt + 1}/{retry} for audio at {offset} to {language}")

                try:
                    subtitles = await audio_to_subtitles(api_key, file, audio_segment_format, language)
                    validate_subtitles(subtitles, duration_ms)                    
                    write_log("Valid", language, offset, subtitles)
                    serialize_subtitles(subtitles, language_code, int(offset))
                    break

                except (SubtitleValidationError, Exception) as e:
                    write_log("Invalid", e, language, offset, subtitles)
                    await asyncio.sleep(min(2 ** attempt, 60))

        except Exception as e:
            print(f"Error: {str(e)}")

        finally:
            await delete_file(api_key, file)
