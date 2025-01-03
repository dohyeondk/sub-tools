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

        if parsed.hls_url:
            change_directory(parsed.output_path)
            hls_to_media(parsed.hls_url, parsed.video_file, False, parsed.overwrite)
            video_to_audio(parsed.video_file, parsed.audio_file, parsed.overwrite)
            media_to_signature(parsed.audio_file, parsed.shazam_signature_file, parsed.overwrite)
            segment_audio(parsed.audio_file, parsed.audio_segment_prefix, parsed.audio_segment_format, parsed.audio_segment_length)
            transcribe(parsed)
            combine_subtitles(parsed.languages)
            print("Done!")
        else:
            parsed.func()

    except Exception as e:
        print(f"Error: {str(e)}")
