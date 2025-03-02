from .arguments.parser import build_parser, parse_args
from .media.converter import hls_to_media, media_to_signature, video_to_audio
from .media.segmenter import segment_audio
from .subtitles.combiner import combine_subtitles
from .system.directory import change_directory
from .system.console import header, success, error
from .transcribe import transcribe


def main():
    parser = build_parser()
    parsed = parse_args(parser)

    try:
        change_directory(parsed.output_path)
        step = 1

        if "video" in parsed.tasks:
            if not parsed.hls_url:
                parsed.func()
                raise Exception("No HLS URL provided")
            header(f"{step}. Download Video")
            hls_to_media(parsed.hls_url, parsed.video_file, False, parsed.overwrite)
            success("Done!")
            step += 1

        if "audio" in parsed.tasks:
            header(f"{step}. Video to Audio")
            video_to_audio(parsed.video_file, parsed.audio_file, parsed.overwrite)
            success("Done!")
            step += 1

        if "signature" in parsed.tasks:
            header(f"{step}. Audio to Signature")
            media_to_signature(parsed.audio_file, parsed.signature_file, parsed.overwrite)
            success("Done!")
            step += 1

        if "segment" in parsed.tasks:
            header(f"{step}. Segment Audio")
            segment_audio(parsed.audio_file, parsed.audio_segment_prefix, parsed.audio_segment_format, parsed.audio_segment_length, parsed.overwrite)
            success("Done!")
            step += 1

        if "transcribe" in parsed.tasks:
            if not (parsed.gemini_api_key and parsed.gemini_api_key.strip()):
                parsed.func()
                raise Exception("No Gemini API Key provided")
            header(f"{step}. Transcribe Audio")
            transcribe(parsed)
            success("Done!")
            step += 1

        if "combine" in parsed.tasks:
            header(f"{step}. Combine Subtitles")
            combine_subtitles(parsed.languages, parsed.audio_segment_prefix, parsed.audio_segment_format)
            success("Done!")
            step += 1

    except Exception as e:
        error(f"Error: {str(e)}")
        exit(1)
