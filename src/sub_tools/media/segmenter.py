import os.path

from typing import Union
from dataclasses import dataclass
from pydub import AudioSegment, silence


@dataclass
class SegmentConfig:
    """
    Configuration for audio segmentation.
    """

    min_silence_length: int = 1_000  # 1 second
    step_down_length: int = 200  # 200 ms
    silence_threshold_db: int = 16  # dB below average segment volume
    search_window_ratio: float = 0.1  # 10% of segment length
    seek_step: int = 100  # 100 ms
    directory: str = "tmp"


def segment_audio(
    audio_file: str,
    audio_segment_prefix: str,
    audio_segment_format: str,
    audio_segment_length: int,
    config: SegmentConfig = SegmentConfig(),
) -> None:
    """
    Segments an audio file using natural pauses.
    """
    first_segment = f"{config.directory}/{audio_segment_prefix}_0.{audio_segment_format}"
    if os.path.exists(first_segment):
        print("Segmented audio files already exist. Skipping segmentation...")
        return

    print(f"Segmenting audio file {audio_file}...")

    audio = AudioSegment.from_file(audio_file, format="mp3")
    segment_ranges = _get_segment_ranges(audio, audio_segment_length, config)

    for start_ms, end_ms in segment_ranges:
        output_file = f"{config.directory}/{audio_segment_prefix}_{start_ms}.{audio_segment_format}"
        partial_audio = audio[start_ms:end_ms]
        partial_audio.export(output_file, format=audio_segment_format)


def _get_segment_ranges(
    audio: AudioSegment,
    segment_length: int,
    config: SegmentConfig,
) -> list[tuple[int, int]]:
    """
    Returns a list of segment ranges for the audio file.
    """
    total_length = len(audio)
    ranges = []
    current_start = 0

    while current_start < total_length:
        remaining_length = total_length - current_start
        if remaining_length <= segment_length:
            ranges.append((current_start, total_length))
            break

        intended_end = current_start + segment_length
        search_window_length = int(segment_length * config.search_window_ratio)
        search_start = max(current_start, intended_end - search_window_length)
        search_end = min(total_length, intended_end + search_window_length)

        split_point = _find_split_point(audio, search_start, search_end, config)

        if split_point:
            ranges.append((current_start, split_point))
            current_start = split_point
        else:
            ranges.append((current_start, intended_end))
            current_start = intended_end

    return ranges


def _find_split_point(
    audio: AudioSegment,
    start_ms: int,
    end_ms: int,
    config: SegmentConfig,
) -> Union[int, None]:
    """
    Find optimal split point in audio segment.
    """
    segment = audio[start_ms:end_ms]
    silence_length = config.min_silence_length

    while silence_length > 0:
        silent_ranges = silence.detect_silence(
            segment,
            min_silence_len=silence_length,
            silence_thresh=segment.dBFS - config.silence_threshold_db,
            seek_step=config.seek_step,
        )

        if silent_ranges and len(silent_ranges) > 0:
            silent_start, silent_end = silent_ranges[0]
            return start_ms + (silent_start + silent_end) // 2

        silence_length -= config.step_down_length

    return None
