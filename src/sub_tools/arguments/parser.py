import argparse

from argparse import ArgumentParser, Namespace
from importlib.metadata import version
from .env_default import EnvDefault


def build_parser() -> ArgumentParser:
    parser = argparse.ArgumentParser(prog="sub-tools", description=None)

    parser.add_argument(
        "--hls-url",
        "-u",
        required=True,
        help="HLS URL (e.g. https://example.com/playlist.m3u8) to download the video from.",
    )

    parser.add_argument(
        "--output-path",
        "-o",
        default="output",
        help="Output path for downloaded files and generated subtitles (default: %(default)s).",
    )

    parser.add_argument(
        "--video-file",
        "-v",
        default="video.mp4",
        help="Path to the video file (default: %(default)s).",
    )

    parser.add_argument(
        "--audio-file",
        "-a",
        default="audio.mp3",
        help="Path to the audio file (default: %(default)s).",
    )

    parser.add_argument(
        "--shazam-signature-file",
        default="message.shazamsignature",
        help="Path to the Shazam signature file (default: %(default)s).",
    )

    parser.add_argument(
        "--overwrite",
        "-y",
        action="store_true",
        help="If given, overwrite the output file if it already exists.",
    )

    parser.add_argument(
        "--gemini-api-key",
        action=EnvDefault,
        env_name="GEMINI_API_KEY",
        help="Gemini API Key. If not provided, the script tries to use the GEMINI_API_KEY environment variable.",
    )

    parser.add_argument(
        "--languages",
        "-l",
        nargs="+",  # allows multiple values, e.g. --languages en es fr
        default=["en", "es", "ko", "zh"],
        help="List of language codes, e.g. --languages en es fr (default: %(default)s).",
    )

    parser.add_argument(
        "--audio-segment-prefix",
        default="audio_segment",
        help="Prefix for audio segments (default: %(default)s).",
    )

    parser.add_argument(
        "--audio-segment-format",
        default="mp3",
        help="Format for audio segments (default: %(default)s).",
    )

    parser.add_argument(
        "--audio-segment-length",
        type=int,
        default=300_000,
        help="Length of each audio segment, in milliseconds (default: %(default)s).",
    )

    parser.add_argument(
        "--retry",
        type=int,
        default=50,
        help="Number of times to retry the tasks (default: %(default)s).",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=version("sub-tools"),
        help="Show program's version number and exit.",
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug mode.")

    def print_help() -> None:
        parser.print_help()

    parser.set_defaults(func=print_help)

    return parser


def parse_args(parser: ArgumentParser) -> Namespace:
    parsed = parser.parse_args()
    return parsed
