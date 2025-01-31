from .arguments.parser import build_parser, parse_args
from .media.converter import hls_to_media, media_to_signature, video_to_audio
from .media.segmenter import segment_audio
from .subtitles.combiner import combine_subtitles
from .system.directory import change_directory
from .transcribe import transcribe


def main():
    try:
        parser = build_parser()
        parsed = parse_args(parser)

        change_directory(parsed.output_path)
        if "video" in parsed.tasks:
            if parsed.hls_url:
                hls_to_media(parsed.hls_url, parsed.video_file, False, parsed.overwrite)
            else:
                print("Error: No HLS URL provided")
                parsed.func()
                exit(1)
        if "audio" in parsed.tasks:
            video_to_audio(parsed.video_file, parsed.audio_file, parsed.overwrite)
        if "signature" in parsed.tasks:
            media_to_signature(parsed.audio_file, parsed.signature_file, parsed.overwrite)
        if "segment" in parsed.tasks:
            segment_audio(parsed.audio_file, parsed.audio_segment_prefix, parsed.audio_segment_format, parsed.audio_segment_length, parsed.overwrite)
        if "transcribe" in parsed.tasks:
            transcribe(parsed)
        if "combine" in parsed.tasks:
            combine_subtitles(parsed.languages, parsed.audio_segment_prefix, parsed.audio_segment_format)
        print("Done!")

    except Exception as e:
        print(f"Error: {str(e)}")
