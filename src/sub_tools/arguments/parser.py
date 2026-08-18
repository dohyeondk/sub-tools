import argparse
from argparse import ArgumentParser, Namespace
from importlib.metadata import version

from ..config import SUPPORTED_PROVIDERS, apply_namespace, config
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
        "--google-api-key",
        dest="gemini_api_key",
        action=EnvDefault,
        env_name="GEMINI_API_KEY",
        required=False,
        help="Google/Gemini API key. Falls back to the GEMINI_API_KEY environment variable.",
    )

    parser.add_argument(
        "--openai-api-key",
        action=EnvDefault,
        env_name="OPENAI_API_KEY",
        required=False,
        help="OpenAI API key. Falls back to the OPENAI_API_KEY environment variable.",
    )

    parser.add_argument(
        "--anthropic-api-key",
        action=EnvDefault,
        env_name="ANTHROPIC_API_KEY",
        required=False,
        help="Anthropic API key. Falls back to the ANTHROPIC_API_KEY environment variable.",
    )

    parser.add_argument(
        "--openrouter-api-key",
        action=EnvDefault,
        env_name="OPENROUTER_API_KEY",
        required=False,
        help="OpenRouter API key. Falls back to the OPENROUTER_API_KEY environment variable.",
    )

    parser.add_argument(
        "--provider",
        choices=SUPPORTED_PROVIDERS,
        default=None,
        help=(
            "Model provider (default: inferred from the model). Choose google, anthropic, "
            "openai, or openrouter; gemini is kept as a compatibility alias for google."
        ),
    )

    parser.add_argument(
        "--model",
        "-m",
        dest="model",
        default=config.model,
        help=(
            "Model for transcription and translation (default: %(default)s). "
            "Use the model identifier from the selected provider, including an OpenRouter "
            "model slug such as google/gemini-2.5-flash."
        ),
    )

    parser.add_argument(
        "--audio-model",
        default=config.audio_model,
        help=(
            "Audio-capable model used for transcription when the main model cannot hear audio. "
            "The identifier is interpreted by the selected provider (for example, "
            "whisper-1 for OpenAI or google/gemini-2.5-flash for OpenRouter)."
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
