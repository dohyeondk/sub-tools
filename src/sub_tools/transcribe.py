import asyncio

from .intelligence.transcriber import audio_to_subtitles
from .subtitles.serializer import serialize_subtitles
from .subtitles.validator import validate_subtitles
from .system.directory import paths_with_offsets
from .system.language import get_language_name
from .system.measure import measure


max_concurrent_tasks = 10
semaphore = asyncio.Semaphore(max_concurrent_tasks)


def transcribe(parsed):
    asyncio.run(__transcribe(parsed))


async def __transcribe(parsed):
    tasks = []

    for path, offset in paths_with_offsets(parsed.audio_segment_prefix, parsed.audio_segment_format):
        for language_code in parsed.languages:
            task = asyncio.create_task(
                transcribe(
                    path,
                    parsed.audio_segment_prefix,
                    parsed.audio_segment_format,
                    offset,
                    language_code,
                    parsed.gemini_api_key,
                    parsed.retry
                )
            )
            tasks.append(task)

    await asyncio.gather(*tasks)


async def transcribe(audio_segment_path, audio_segment_prefix, audio_segment_format, offset, language_code, api_key, retry):
    async with semaphore:
        language = get_language_name(language_code)

        for i in range(0, retry):
            print(f"Transcribe the audio at {offset} to {language}.")
            with measure():
                subtitles = await audio_to_subtitles(audio_segment_path, audio_segment_format, language, api_key)
            if validate_subtitles(subtitles, offset, audio_segment_prefix, audio_segment_format):
                serialize_subtitles(subtitles, language_code, int(offset))
                break
            else:
                await asyncio.sleep(10)
