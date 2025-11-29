import argparse
from argparse import ArgumentParser, Namespace
from importlib.metadata import version

from .env_default import EnvDefault


def _resolve_version() -> str:
    """Return package version; fall back to a local dev string when unavailable."""
    try:
        return version("sub-tools")
    except Exception:
        # When running from source without installation, metadata lookup can fail.
        return "0.0.0+local"


def build_parser() -> ArgumentParser:
    parser = argparse.ArgumentParser(prog="sub-tools", description=None)

    parser.add_argument(
        "--tasks",
        "-t",
        nargs="+",
        default=["video", "audio", "signature", "transcribe"],
        help="List of tasks to perform (default: %(default)s).",
    )

    parser.add_argument(
        "-i",
        "--url",
        "--hls-url",  # Keep for backward compatibility
        dest="url",
        help="URL to download media from. Supports both HLS streams (e.g., https://example.com/playlist.m3u8) and direct file URLs (e.g., https://example.com/video.mp4).",
    )

    parser.add_argument(
        "-v",
        "--video-file",
        default="output/video.mp4",
        help="Path to the video file (default: %(default)s).",
    )

    parser.add_argument(
        "-a",
        "--audio-file",
        default="output/audio.mp3",
        help="Path to the audio file (default: %(default)s).",
    )

    parser.add_argument(
        "-s",
        "--signature-file",
        default="output/message.shazamsignature",
        help="Path to the Shazam signature file (default: %(default)s).",
    )

    parser.add_argument(
        "-l",
        "--languages",
        nargs="+",  # allows multiple values, e.g. --languages en es fr
        default=["en"],
        help="List of language codes, e.g. --languages en es fr (default: %(default)s).",
    )

    parser.add_argument(
        "-o",
        "--output",
        dest="output_file",
        default=None,
        help="Custom output filename for combined subtitles (e.g., 'output.srt'). Language code will be inserted before extension.",
    )

    parser.add_argument(
        "--overwrite",
        "-y",
        action="store_true",
        help="If given, overwrite the output file if it already exists.",
    )

    parser.add_argument(
        "--retry",
        "-r",
        type=int,
        default=50,
        help="Number of times to retry the tasks (default: %(default)s).",
    )

    parser.add_argument(
        "--gemini-api-key",
        action=EnvDefault,
        env_name="GEMINI_API_KEY",
        help="Gemini API Key. If not provided, the script tries to use the GEMINI_API_KEY environment variable.",
    )

    parser.add_argument(
        "--model",
        "-m",
        default="gemini-2.5-flash-lite",
        help="Gemini model to use for transcription (default: %(default)s).",
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug mode.")

    parser.add_argument(
        "--version",
        action="version",
        version=_resolve_version(),
        help="Show program's version number and exit.",
    )

    def print_help() -> None:
        parser.print_help()

    parser.set_defaults(func=print_help)

    return parser


def parse_args(parser: ArgumentParser) -> Namespace:
    parsed = parser.parse_args()
    return parsed
