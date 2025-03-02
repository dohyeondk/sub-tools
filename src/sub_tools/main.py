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

        if "video" in parsed.tasks:
            if not parsed.hls_url:
                parsed.func()
                raise Exception("No HLS URL provided")
            header("Download Video")
            hls_to_media(parsed.hls_url, parsed.video_file, parsed.overwrite)

        if "audio" in parsed.tasks:
            header("Convert Video to Audio")
            video_to_audio(parsed.video_file, parsed.audio_file, parsed.overwrite)

        if "signature" in parsed.tasks:
            header("Convert Audio to Signature")
            media_to_signature(parsed.audio_file, parsed.signature_file, parsed.overwrite)

        if "segment" in parsed.tasks:
            header("Segment Audio")
            segment_audio(parsed.audio_file, parsed.audio_segment_prefix, parsed.audio_segment_format, parsed.audio_segment_length, parsed.overwrite)

        if "transcribe" in parsed.tasks:
            if not (parsed.gemini_api_key and parsed.gemini_api_key.strip()):
                parsed.func()
                raise Exception("No Gemini API Key provided")
            header("Transcribe Audio")
            transcribe(parsed)

        if "combine" in parsed.tasks:
            header("Combine Subtitles")
            combine_subtitles(parsed.languages, parsed.audio_segment_prefix, parsed.audio_segment_format)

        success("Done!")

    except Exception as e:
        error(f"Error: {str(e)}")
        exit(1)
