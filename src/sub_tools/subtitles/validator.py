import re
import pysrt


def validate_subtitles(content, duration):
    """
    Validate a string of subtitles to ensure they meet the following criteria:

    1. The subtitles can be successfully parsed into a list of items.
    2. There is more than one subtitle item.
    3. No subtitle item's duration exceeds the maximum allowed limit.
    4. The first subtitle does not start too late.
    5. The last subtitle does not end too far from the provided duration.
    6. For each subtitle item, the start time is not greater than the end time.

    Parameters:
        content (str): The subtitles as a string in SRT format.
        duration (int): The total duration (in ms) of the audio or video segment.

    Returns:
        bool: True if the subtitles are valid, False otherwise.
    """
    max_valid_duration = 20_000    # Maximum allowed duration for any single subtitle (ms)
    begin_gap_threshold = 5_000    # Maximum allowed gap at the beginning (ms)
    end_gap_threshold = 20_000     # Maximum allowed gap at the end (ms)

    # Parse the subtitles string into a list of subtitle items.
    try:
        subs = pysrt.from_string(content)
    except AttributeError:
        print("Error: Invalid subtitles detected (cannot parse subtitles).")
        return False

    # Check if there is more than one subtitle item.
    if len(subs) <= 1:
        print("Error: Not enough subtitles to validate.")
        return False

    # Validate that no subtitle item exceeds the maximum allowed duration.
    for item in subs:
        if item.duration.ordinal > max_valid_duration:
            print(f"Error: A subtitle item ({item.start} --> {item.end}) exceeds the maximum allowed duration.")
            return False

    # Ensure the first subtitle does not start too late.
    begin_gap = abs(subs[0].start.ordinal)
    if begin_gap > begin_gap_threshold:
        print(f"Error: Too much gap in the beginning ({begin_gap} ms).")
        return False

    # Ensure the last subtitle does not end too far from the provided duration.
    end_gap = abs(subs[-1].end.ordinal - duration)
    if end_gap > end_gap_threshold:
        print(f"Error: Too much gap at the end ({end_gap} ms).")
        return False

    # Validate that the start time is never greater than the end time in any subtitle.
    for item in subs:
        if item.start > item.end:
            print(f"Error: Start time ({item.start}) is greater than end time ({item.end}).")
            return False

    return True


def fix_subtitles(content):
    """
    Fix timestamps within an SRT-formatted string that are missing the hour part.

    Each timestamp should have the format: HH:MM:SS,mmm. If a line
    is found with only MM:SS,mmm (missing hours), this function will
    prepend "00:" to make it valid. For example: `"02:27,170 --> 02:28,430"`
    becomes `"00:02:27,170 --> 00:02:28,430"`.

    Parameters:
        content (str): A string containing subtitles (possibly invalid) in SRT format.

    Returns:
        str: A string with corrected subtitle timestamps.
    """
    lines = [__fix_subtitle_line(line) for line in content.splitlines()]
    return "\n".join(lines)

def __fix_subtitle_line(line):
    pattern = r'^(\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2},\d{3})$'
    match = re.match(pattern, line.strip())
    if match:
        left_timestamp, right_timestamp = match.groups()
        fixed_left = __fix_subtitle_timestamp(left_timestamp)
        fixed_right = __fix_subtitle_timestamp(right_timestamp)
        return f"{fixed_left} --> {fixed_right}"
    else:
        return line

def __fix_subtitle_timestamp(timestamp):
    if timestamp.count(':') == 1:
        timestamp = "00:" + timestamp
    return timestamp
