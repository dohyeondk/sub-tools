import asyncio

from .intelligence.client import audio_to_subtitles, upload_file, delete_file
from .media.info import get_duration
from .subtitles.serializer import serialize_subtitles
from .subtitles.validator import validate_subtitles
from .system.directory import paths_with_offsets
from .system.language import get_language_name
from .system.logger import write_log
from .system.measure import measure


max_concurrent_tasks = 4
semaphore = asyncio.Semaphore(max_concurrent_tasks)


def transcribe(parsed):
    asyncio.run(__transcribe(parsed))


async def __transcribe(parsed):
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


async def __transcribe_item(audio_segment_path, audio_segment_format, offset, language_code, api_key, retry):
    async with semaphore:
        language = get_language_name(language_code)

        file = await upload_file(api_key, audio_segment_path)
        duration_ms = get_duration(audio_segment_path) * 1000

        for i in range(0, retry):
            print(f"Transcribe the audio at {offset} to {language}.")
            with measure():
                subtitles = await audio_to_subtitles(api_key, file, audio_segment_format, language)
            if validate_subtitles(subtitles, duration_ms):
                write_log("Valid", language, offset, subtitles)
                serialize_subtitles(subtitles, language_code, int(offset))
                break
            else:
                write_log("Invalid", language, offset, subtitles)
                await asyncio.sleep(1 + i)

        await delete_file(api_key, file)
