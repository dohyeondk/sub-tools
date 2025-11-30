from sub_tools.intelligence.gemini import proofread, translate

from .arguments.parser import build_parser, parse_args
from .config import config
from .intelligence.whisperx import transcribe
from .media.converter import download_from_url, media_to_signature, video_to_audio
from .system.console import error, header
from .system.file import ensure_output_directory


def main():
    parser = build_parser()
    parsed = parse_args(parser)

    step = 1

    try:
        ensure_output_directory(config.output_directory)

        if "video" in config.tasks:
            header(f"{step}. Download Video")
            if not config.url:
                parsed.func()
                raise Exception("No URL provided")
            download_from_url()
            step += 1

        if "audio" in config.tasks:
            header(f"{step}. Video to Audio")
            video_to_audio()
            step += 1

        if "signature" in config.tasks:
            header(f"{step}. Audio to Signature")
            media_to_signature()
            step += 1

        if "transcribe" in config.tasks:
            header(f"{step}. Transcribe")
            transcribe()
            step += 1

        if "translate" in config.tasks:
            if not (config.gemini_api_key and config.gemini_api_key.strip()):
                parsed.func()
                raise Exception("No Gemini API Key provided")

            header(f"{step}. Proofread & Translate")
            proofread()
            translate()
            step += 1

    except Exception as e:
        error(f"Error: {str(e)}")
        exit(1)
