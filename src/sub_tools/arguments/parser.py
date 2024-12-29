import argparse


def build_parser():
    parser = argparse.ArgumentParser(prog='sub-tools', description=None)

    parser.add_argument(
        "--hls-url",
        "-u",
        required=True,
        help="HLS URL (e.g. https://example.com/playlist.m3u8) to download the video from."
    )

    parser.add_argument(
        "--output-path",
        "-o",
        default="output",
        help="Output path for downloaded files and generated subtitles."
    )

    parser.add_argument(
        "--video-file",
        "-v",
        default="video.mp4",
        help="Path to the video file (e.g., video.mp4)."
    )

    parser.add_argument(
        "--audio-file",
        "-a",
        default="audio.mp3",
        help="Path to the audio file (e.g., audio.mp3)."
    )

    parser.add_argument(
        "--overwrite",
        "-y",
        action="store_true",
        help="If given, overwrite the output file if it already exists."
    )

    def print_help() -> None:
        parser.print_help()
    parser.set_defaults(func=print_help)

    return parser


def parse_args(parser):
    parsed = parser.parse_args()
    return parsed
