import asyncio

from .arguments.parser import build_parser, parse_args
from .intelligence.transcriber import Transcriber
from .media.converter import hls_to_video, video_to_audio, media_to_signature
from .media.segmenter import segment_audio
from .subtitles.combiner import combine_subtitles
from .subtitles.serializer import serialize_subtitles
from .subtitles.validator import validate_subtitles
from .system.directory import change_directory, paths_with_offsets
from .system.language import get_language_name
from .system.measure import measure


max_concurrent_tasks = 6
semaphore = asyncio.Semaphore(max_concurrent_tasks)


def main():
    parser = build_parser()
    parsed = parse_args(parser)
    if parsed.hls_url:
        change_directory(parsed.output_path)
        hls_to_video(parsed.hls_url, parsed.video_file, parsed.overwrite)
        video_to_audio(parsed.video_file, parsed.audio_file, parsed.overwrite)
        media_to_signature(parsed.audio_file, parsed.shazam_signature_file, parsed.overwrite)
        segment_audio(parsed.audio_file)
        asyncio.run(audio_segments_to_srt(parsed))
        combine_subtitles(parsed.languages)
    else:
        parsed.func()


async def audio_segments_to_srt(parsed):
    tasks = []

    for path, offset in paths_with_offsets(parsed.audio_segment_prefix, parsed.audio_segment_format):
        for language_code in parsed.languages:
            task = transcribe(path, parsed.audio_segment_prefix, parsed.audio_segment_format, offset, language_code, parsed.gemini_api_key, parsed.retry)
            tasks.append(task)

    await asyncio.gather(*tasks)


async def transcribe(audio_segment_path, audio_segment_prefix, audio_segment_format, offset, language_code, api_key, retry):
    async with semaphore:
        transcriber = Transcriber(audio_segment_path, audio_segment_format, api_key)
        language = get_language_name(language_code)

        for i in range(0, retry):
            print(f"Transcribe the audio at {offset} to {language}.")
            with measure():
                subtitles = await transcriber.transcribe(language)
            if validate_subtitles(subtitles, offset, audio_segment_prefix, audio_segment_format):
                serialize_subtitles(subtitles, language_code, int(offset))
                break
            else:
                await asyncio.sleep(10)
