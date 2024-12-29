import os.path

from pydub import AudioSegment, silence


def segment_audio(
    audio_file,
    audio_segment_format='mp3',
    audio_segment_prefix='audio_segment',
):
    """
    Segments an audio file by first determining split points from natural pauses,
    then exporting each segment as a separate audio file.

    :param audio_file: Path to the source audio file
    :param audio_segment_format: Audio format for exported segments (default: 'mp3')
    :param audio_segment_prefix: File prefix for each exported segment (default: 'audio_segment')
    """
    if os.path.exists(f"{audio_segment_prefix}_0.{audio_segment_format}"):
        print("Segmented audio files already exist. Skipping segmentation...")
        return

    segment_ranges = __ranges_split_by_natural_pauses(audio_file=audio_file)
    audio = AudioSegment.from_file(audio_file)

    for segment_range in segment_ranges:
        start_ms, end_ms = segment_range
        partial_audio = audio[start_ms:end_ms]
        audio_segment_filename = f"{audio_segment_prefix}_{start_ms}.{audio_segment_format}"
        partial_audio.export(audio_segment_filename, format=audio_segment_format)


def __ranges_split_by_natural_pauses(
    audio_file,
    segment_length_ms=600_000,  # 10 minutes
    search_before_ms=60_000,    # 1 minute
):
    """
    Splits an audio file into segments close to `segment_length_ms`,
    but tries to avoid cutting through speech by looking for natural pauses.

    1. For the first segment, looks between (segment_length_ms - search_before_ms)
       and segment_length_ms for a suitable pause. If found, uses that as a split point.
    2. If no pause is found, tries shorter silences by stepping down.
    3. Repeats until the entire file is processed.

    :param audio_file: Path to the source audio file
    :param segment_length_ms: Desired maximum segment length in ms (default 10 minutes)
    :param search_before_ms: How far before the exact segment length to start looking for silence (default 1 minute)
    :return: List of (start_ms, end_ms) tuples for each segment
    """
    audio = AudioSegment.from_file(audio_file, format="mp3")
    total_length_ms = len(audio)

    split_ranges = []
    current_start = 0

    while True:
        print("hello")
        # If remaining audio is less than the desired segment length, we're done
        if (total_length_ms - current_start) <= segment_length_ms:
            split_ranges.append((current_start, total_length_ms))
            break

        intended_end = current_start + segment_length_ms
        search_start = max(current_start, intended_end - search_before_ms)
        search_end = min(total_length_ms, intended_end)

        # Attempt to find a pause in that search window
        pause_ms = __find_split_point(audio, search_start, search_end)

        if pause_ms is not None:
            # Found a pause in the search window
            split_ranges.append((current_start, pause_ms))
            current_start = pause_ms
        else:
            # No suitable pause found; split exactly at intended_end
            split_ranges.append((current_start, intended_end))
            current_start = intended_end

    return split_ranges


def __find_split_point(
    audio_segment,
    start_ms,
    end_ms,
    min_silence_length=1_000,  # 1 second
    step_down_length=200,      # 200 ms
):
    """
    Searches for a pause (silence) between start_ms and end_ms within a given AudioSegment.

    1. Looks for a silence at least `min_silence_length` ms long.
    2. If not found, decreases `min_silence_length` by `step_down_length` ms each iteration
       until a pause is found or a minimum threshold is reached.

    :param audio_segment: A pydub AudioSegment object
    :param start_ms: Start time in milliseconds for the search window
    :param end_ms: End time in milliseconds for the search window
    :param min_silence_length: Initial desired silence length in ms (default 1 second)
    :param step_down_length: Step by which to reduce silence length if not found (default 200 ms)
    :return: Split point in ms, or None if no suitable pause is found
    """

    # Define the segment in which we search for silence
    segment_to_search = audio_segment[start_ms:end_ms]

    # Step down from the desired silence length until we find a match or give up
    current_silence_length = min_silence_length
    while current_silence_length > 0:
        print("hi")
        silent_ranges = silence.detect_silence(
            segment_to_search,
            min_silence_len=current_silence_length,
            silence_thresh=segment_to_search.dBFS - 16,
            seek_step=100
        )

        if silent_ranges:
            # If we found at least one silent range, pick the midpoint of the first found
            first_silent_range = silent_ranges[0]
            split_point_relative = (first_silent_range[0] + first_silent_range[1]) // 2
            return start_ms + split_point_relative

        current_silence_length -= step_down_length

    # No suitable pause found
    return None
