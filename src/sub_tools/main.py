from .arguments.parser import build_parser, parse_args
from .media.converter import hls_to_video, video_to_audio
from .media.segmenter import segment_audio
from .system.directory import change_directory


def main():
    parser = build_parser()
    parsed = parse_args(parser)
    if parsed.hls_url:
        change_directory(parsed.output_path)
        hls_to_video(parsed.hls_url, parsed.video_file, parsed.overwrite)
        video_to_audio(parsed.video_file, parsed.audio_file, parsed.overwrite)
        segment_audio(parsed.audio_file)
    else:
        parsed.func()
