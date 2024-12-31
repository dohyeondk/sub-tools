import pysrt
from pydub import AudioSegment


def validate_subtitles(content, offset, audio_segment_prefix, audio_segment_format):
    """
    Validates a string of subtitles to ensure they meet the following criteria:
    1. The subtitles can be successfully parsed into a list of items.
    2. No subtitle item's duration exceeds the maximum allowed limit.

    Parameters:
        content (str): The subtitles as a string in SRT format.
        offset (int): The offset of the subtitle to validate.
        audio_segment_prefix (str): The prefix of the audio segment.
        audio_segment_format (str): The format of the audio segment.

    Returns:
        bool: True if the subtitles are valid, False otherwise.
    """
    max_valid_duration = 20_000
    start_diff_threshold = 5_000
    end_diff_threshold = 20_000

    # Parse the subtitles string into a list of subtitle items.
    try:
        subs = pysrt.from_string(content)
    except AttributeError:
        print("Error: Invalid subtitles detected.")
        return False

    # Check if there are no subtitle items.
    if len(subs) <= 1:
        print("Error: Not enough subtitles to validate.")
        return False

    # Validate that no subtitle item exceeds the maximum allowed duration.
    for item in subs:
        if item.duration.ordinal > max_valid_duration:
            print("Error: Too long item duration.")
            return False

    # Validate if the subtitle has enough duration
    audio = AudioSegment.from_file(f"{audio_segment_prefix}_{offset}.{audio_segment_format}")
    diff = abs(subs[0].start.ordinal - 0)
    if diff > start_diff_threshold:
        print(f"Error: Too much gap in the beginning ({diff}).")
        return False
    diff = abs(subs[-1].end.ordinal - audio.duration_seconds * 1000)
    if diff > end_diff_threshold:
        print(f"Error: Too much gap in the end ({diff}).")
        return False

    return True
