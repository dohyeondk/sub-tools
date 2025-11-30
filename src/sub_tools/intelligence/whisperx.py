import whisperx

from sub_tools.system.file import should_skip

from ..config import config
from ..subtitles.serializer import serialize_subtitles


def transcribe() -> None:
    print(config.srt_file)
    if should_skip(config.srt_file):
        return

    try:
        # Load model
        model = whisperx.load_model(
            config.whisperx_model,
            device=config.whisperx_device,
            compute_type=config.whisperx_compute_type,
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
