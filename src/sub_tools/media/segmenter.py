import glob
from dataclasses import dataclass

from pydub import AudioSegment
from silero_vad import load_silero_vad, read_audio, get_speech_timestamps

from ..system.console import warning, status


@dataclass
class SegmentConfig:
    """
    Configuration for audio segmentation.
    """
    min_segment_length: int = 200  # 200 ms
    min_silent_length: int = 200  # 200 ms
    max_silence_length: int = 3_000  # 3 seconds
    threshold: float = 0.5
    directory: str = "tmp"


def segment_audio(
    audio_file: str,
    audio_segment_prefix: str,
    audio_segment_format: str,
    audio_segment_length: int,
    overwrite: bool = False,
    config: SegmentConfig = SegmentConfig(),
) -> None:
    """
    Segments an audio file using natural pauses.
    """
    pattern = f"{config.directory}/{audio_segment_prefix}_[0-9]*.{audio_segment_format}"
    if glob.glob(pattern) and not overwrite:
        warning("Segmented audio files already exist. Skipping segmentation...")
        return

    with status("Segmenting audio..."):
        model = load_silero_vad()
        wav = read_audio(audio_file)
        speech_timestamps = get_speech_timestamps(
            wav,
            model,
            threshold=config.threshold,
            min_speech_duration_ms=config.min_segment_length,
            max_speech_duration_s=float(audio_segment_length) / 1000.0,
            min_silence_duration_ms=config.min_silent_length,
            return_seconds=True
        )

        segment_ranges = [(int(x['start'] * 1000), int(x['end'] * 1000)) for x in speech_timestamps]
        segment_ranges = _group_ranges(segment_ranges, config.max_silence_length, audio_segment_length)

        audio = AudioSegment.from_file(audio_file, format="mp3")

        for start_ms, end_ms in segment_ranges:
            output_file = f"{config.directory}/{audio_segment_prefix}_{start_ms}.{audio_segment_format}"
            partial_audio = audio[start_ms:end_ms]
            partial_audio.export(output_file, format=audio_segment_format)


def _group_ranges(
    ranges: list[tuple[int, int]],
    max_silence_length: int,
    max_segment_length: int,
) -> list[tuple[int, int]]:
    """
    Combines ranges that are within max_silence_length of each other.
    """
    if not ranges:
        return []

    grouped = [ranges[0]]
    for curr in ranges[1:]:
        if curr[0] - grouped[-1][1] <= max_silence_length and curr[1] - grouped[-1][0] <= max_segment_length:
            grouped[-1] = (grouped[-1][0], curr[1])
        else:
            grouped.append(curr)

    return grouped
