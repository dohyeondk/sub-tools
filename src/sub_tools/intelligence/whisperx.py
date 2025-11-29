"""
WhisperX client for initial English transcription.
"""

import os
from typing import Union

import whisperx

from ..subtitles.serializer import serialize_subtitles_from_whisperx


def audio_to_srt_with_whisperx(
    audio_path: str,
    output_directory: str,
    device: str,
    compute_type: str,
    model_name: str,
) -> Union[str, None]:
    """
    Transcribe audio file to SRT using WhisperX.

    Args:
        audio_path: Path to the audio file
        output_directory: Directory to save the SRT file
        device: Device to run inference on ("cpu", "cuda")
        compute_type: Compute type for faster-whisper ("int8", "float16", "float32")
        model_name: WhisperX model to use (e.g., "base.en", "small.en", "medium.en", "large-v2")

    Returns:
        Path to the generated SRT file, or None if transcription failed
    """
    try:
        # Load model
        model = whisperx.load_model(
            model_name, device=device, compute_type=compute_type
        )

        # Transcribe audio
        audio = whisperx.load_audio(audio_path)
        result = model.transcribe(audio, batch_size=16)

        # Align whisper output
        model_a, metadata = whisperx.load_align_model(language_code="en", device=device)
        result = whisperx.align(
            result["segments"],
            model_a,
            metadata,
            audio,
            device,
            return_char_alignments=False,
        )

        # Save as SRT
        srt_path = os.path.join(output_directory, "en_whisperx.srt")
        serialize_subtitles_from_whisperx(result["segments"], srt_path)

        # Save as JSON
        json_path = os.path.join(output_directory, "en_whisperx.json")
        import json
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        return srt_path

    except Exception as e:
        print(f"WhisperX transcription failed: {str(e)}")
        return None
