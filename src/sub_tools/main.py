from .arguments.parser import build_parser, parse_args
from .config import config
from .media.converter import download_from_url, media_to_signature, video_to_audio
from .system.console import error, header, success
from .system.directory import ensure_output_directory, get_temp_directory
from .transcribe import (
    proofread_with_gemini,
    transcribe_with_whisperx,
    translate_with_gemini,
)


def main():
    parser = build_parser()
    parsed = parse_args(parser)

    try:
        # Ensure output directory exists for final files
        ensure_output_directory()

        # Get temp directory for WIP files (URL-based if provided)
        temp_dir = get_temp_directory(parsed.url)
        print(temp_dir)

        # Create unified config
        config.directory = temp_dir
        config.output_file = parsed.output_file
        config.gemini_api_key = parsed.gemini_api_key
        config.gemini_model = parsed.model

        step = 1

        if "video" in parsed.tasks:
            if not parsed.url:
                parsed.func()
                raise Exception("No URL provided")
            header(f"{step}. Download Video")
            download_from_url(parsed.url, parsed.video_file, False, parsed.overwrite)
            success("Done!")
            step += 1

        if "audio" in parsed.tasks:
            header(f"{step}. Video to Audio")
            video_to_audio(parsed.video_file, parsed.audio_file, parsed.overwrite)
            success("Done!")
            step += 1

        if "signature" in parsed.tasks:
            header(f"{step}. Audio to Signature")
            media_to_signature(
                parsed.audio_file, parsed.signature_file, parsed.overwrite
            )
            success("Done!")
            step += 1

        if "transcribe" in parsed.tasks:
            if not (parsed.gemini_api_key and parsed.gemini_api_key.strip()):
                parsed.func()
                raise Exception("No Gemini API Key provided")

            header(f"{step}. Transcribe with WhisperX")
            whisperx_srt_path = transcribe_with_whisperx(parsed)
            success("Done!")

            header(f"{step}. Proofread with Gemini")
            english_srt_path = proofread_with_gemini(parsed, whisperx_srt_path)
            success("Done!")

            header(f"{step}. Translate to Target Languages")
            translate_with_gemini(parsed, english_srt_path)
            success("Done!")
            step += 1

    except Exception as e:
        error(f"Error: {str(e)}")
        exit(1)
