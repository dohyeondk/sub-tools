import glob

from typing import Union
from dataclasses import dataclass
from pydub import AudioSegment, silence


@dataclass
class SegmentConfig:
    """
    Configuration for audio segmentation.
    """

    min_segment_length: int = 200  # 200 ms
    max_silence_length: int = 3_000  # 3 seconds
    silent_length: int = 1_000  # 1 second
    silent_length_decrement: int = 200  # 200 ms
    silence_threshold_db: int = -32
    seek_step: int = 10
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
        current_end = current_start + min(segment_length, total_length - current_start)
        split_range = _find_split_range(audio, current_start, current_end, config)

        if split_range:
            start_ms, end_ms = split_range
            if end_ms - start_ms >= config.min_segment_length:
                ranges.append((start_ms, end_ms))
            current_start = end_ms
        else:
            current_start = current_end

    return ranges


def _find_split_range(
    audio: AudioSegment,
    start_ms: int,
    end_ms: int,
    config: SegmentConfig,
) -> Union[tuple[int, int], None]:
    """
    Find optimal split points in audio segment.
    """
    segment = audio[start_ms:end_ms]
    non_silent_ranges = []

    for silent_length in range(config.silent_length, 0, -config.silent_length_decrement):
        ranges = silence.detect_nonsilent(
            segment,
            min_silence_len=silent_length,
            silence_thresh=segment.dBFS + config.silence_threshold_db,
            seek_step=config.seek_step,
        )

        non_silent_ranges = [(r[0] + start_ms, r[1] + start_ms) for r in ranges]

        if len(non_silent_ranges) > 1:
            non_silent_ranges = [r for r in non_silent_ranges if r[1] < end_ms]
            break

    if len(non_silent_ranges) == 0:
        non_silent_ranges = [(start_ms, end_ms)]

    non_silent_ranges = _filter_ranges(non_silent_ranges, config.max_silence_length)

    if len(non_silent_ranges) > 0:
        start_ms, end_ms = non_silent_ranges[0][0], non_silent_ranges[-1][1]
        return (start_ms, end_ms)

    return None


def _filter_ranges(
    ranges: list[tuple[int, int]],
    max_silence_length: int,
) -> list[tuple[int, int]]:
    """
    Filters ranges by keeping only consecutive segments within max_silence_length.
    """
    if not ranges:
        return []
    
    filtered_ranges = [ranges[0]]
    for current_range in ranges[1:]:
        if current_range[0] - filtered_ranges[-1][1] > max_silence_length:
            break
        filtered_ranges.append(current_range)

    return filtered_ranges
