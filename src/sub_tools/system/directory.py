import os
import re


def change_directory(directory):
    os.makedirs(directory, exist_ok=True)
    os.chdir(directory)


def paths_with_offsets(prefix, file_format):
    pattern = fr"{prefix}_(\d+)\.{file_format}"
    return [
        (audio_segment_path, match.group(1))
        for audio_segment_path in sorted(os.listdir("."))
        for match in [re.match(pattern, audio_segment_path)]
        if match and match.group(1)
    ]
