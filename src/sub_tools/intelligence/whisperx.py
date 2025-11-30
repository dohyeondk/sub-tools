import logging
import os
import sys
import warnings
from contextlib import contextmanager

import whisperx

from sub_tools.system.console import info
from sub_tools.system.file import should_skip

from ..config import config
from ..subtitles.serializer import serialize_subtitles


def transcribe() -> None:
    if should_skip(config.srt_file):
        return

    info("Transcribing audio using WhisperX...")

    try:
        with _suppress_whisperx_output():
            # Load model
            model = whisperx.load_model(
                config.whisperx_model,
                device=config.whisperx_device,
                compute_type=config.whisperx_compute_type,
                language=config.source_language,
            )

            # Transcribe audio
            audio = whisperx.load_audio(config.audio_file)
            result = model.transcribe(audio, batch_size=config.whisperx_batch_size)

            # Align whisper output
            model_a, metadata = whisperx.load_align_model(
                language_code=config.source_language, device=config.whisperx_device
            )
            result = whisperx.align(
                result["segments"],
                model_a,
                metadata,
                audio,
                config.whisperx_device,
                return_char_alignments=False,
            )

            # Save as SRT
            serialize_subtitles(result["segments"], config.srt_file)

    except Exception as e:
        print(f"WhisperX transcription failed: {str(e)}")
        raise


@contextmanager
def _suppress_whisperx_output():
    """
    Context manager to suppress all WhisperX/pyannote output unless in debug mode.

    Suppresses:
    - All warnings from whisperx, pyannote, pytorch_lightning, and torch
    - All logging output from these libraries
    - All stdout/stderr output
    """
    if config.debug:
        yield
        return

    # Suppress warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")

        # Suppress logging
        logging_modules = [
            "whisperx",
            "pyannote",
            "pytorch_lightning",
            "lightning",
            "torch",
        ]
        original_levels = {}
        for module_name in logging_modules:
            logger = logging.getLogger(module_name)
            original_levels[module_name] = logger.level
            logger.setLevel(logging.ERROR)

        # Suppress stdout/stderr
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        with open(os.devnull, "w") as devnull:
            sys.stdout = devnull
            sys.stderr = devnull

            try:
                yield
            finally:
                # Restore stdout/stderr
                sys.stdout = original_stdout
                sys.stderr = original_stderr

                # Restore logging levels
                for module_name, level in original_levels.items():
                    logging.getLogger(module_name).setLevel(level)
