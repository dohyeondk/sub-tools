import argparse
from argparse import ArgumentParser, Namespace
from importlib.metadata import version

from ..config import apply_namespace, config
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
        default=list(config.tasks),
        help=(
            "List of tasks to perform (default: %(default)s). "
            "Add 'dub' to speak the generated subtitles into a translated MP3 per language."
        ),
    )

    parser.add_argument(
        "-i",
        "--url",
        "--hls-url",  # Keep for backward compatibility
        dest="url",
        help="URL to download media from. Supports both HLS streams (e.g., https://example.com/playlist.m3u8) and direct file URLs (e.g., https://example.com/video.mp4).",
    )

    parser.add_argument(
        "--video-file",
        default=config.video_file,
        help="Filename for the downloaded video inside the output directory (default: %(default)s).",
    )

    parser.add_argument(
        "--audio-file",
        default=config.audio_file,
        help="Filename for the extracted audio inside the output directory (default: %(default)s).",
    )

    parser.add_argument(
        "--signature-file",
        default=config.signature_file,
        help="Filename for the Shazam signature inside the output directory (default: %(default)s).",
    )

    parser.add_argument(
        "--source-language",
        default=config.source_language,
        help="Source language code. (default: %(default)s).",
    )

    parser.add_argument(
        "-l",
        "--languages",
        nargs="+",  # allows multiple values, e.g. --languages en es fr
        default=list(config.languages),
        help="List of language codes, e.g. --languages en es fr (default: %(default)s).",
    )

    parser.add_argument(
        "-o",
        "--output",
        dest="output_directory",
        default=config.output_directory,
        help="Directory where generated files will be saved (default: %(default)s).",
    )

    parser.add_argument(
        "--overwrite",
        "-y",
        action="store_true",
        default=config.overwrite,
        help="If given, overwrite the output file if it already exists.",
    )

    parser.add_argument(
        "--retry",
        "-r",
        type=int,
        default=config.retry,
        help="Number of times to retry the tasks (default: %(default)s).",
    )

    parser.add_argument(
        "--gemini-api-key",
        action=EnvDefault,
        env_name="GEMINI_API_KEY",
        required=False,
        help="Gemini API Key. If not provided, the script tries to use the GEMINI_API_KEY environment variable.",
    )

    parser.add_argument(
        "--openai-api-key",
        action=EnvDefault,
        env_name="OPENAI_API_KEY",
        required=False,
        help="OpenAI API Key, used when an OpenAI model is selected. If not provided, the script tries to use the OPENAI_API_KEY environment variable.",
    )

    parser.add_argument(
        "--model",
        "-m",
        dest="model",
        default=config.model,
        help=(
            "Model for transcription and translation (default: %(default)s). "
            "Gemini models use the Gemini API; OpenAI models such as gpt-5.6-luna use the OpenAI API."
        ),
    )

    parser.add_argument(
        "--audio-model",
        default=config.audio_model,
        help=(
            "Model that listens to the audio when the main model cannot. OpenAI text models "
            "such as gpt-5.6-luna transcribe through this model (default: whisper-1 via the "
            "transcription API; gpt-audio-* models are also accepted); Gemini models hear "
            "audio natively and ignore it."
        ),
    )

    parser.add_argument(
        "--tts-model",
        default=config.tts_model,
        help="Text-to-speech model for the dub task (default: the selected provider's cheapest TTS model).",
    )

    parser.add_argument(
        "--tts-voice",
        default=config.tts_voice,
        help="Voice for the dub task (default: the selected provider's default voice).",
    )

    parser.add_argument(
        "--begin-gap-threshold",
        type=int,
        default=config.begin_gap_threshold,
        help="Maximum allowed silence before the first subtitle, in ms (default: %(default)s). Raise it for media with music intros.",
    )

    parser.add_argument(
        "--end-gap-threshold",
        type=int,
        default=config.end_gap_threshold,
        help="Maximum allowed silence after the last subtitle, in ms (default: %(default)s). Raise it for media with credits or outros.",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        default=config.debug,
        help="Enable debug mode.",
    )

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
    apply_namespace(parsed)
    return parsed
