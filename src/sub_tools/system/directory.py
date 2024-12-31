import os
import re


def change_directory(directory: str) -> None:
    """Changes the current working directory to the specified directory."""
    os.makedirs(directory, exist_ok=True)
    os.chdir(directory)


def paths_with_offsets(prefix: str, file_format: str) -> list[tuple[str, int]]:
    """Returns a list of paths with offsets."""
    pattern = fr"{prefix}_(\d+)\.{file_format}"
    return [
        (audio_segment_path, match.group(1))
        for audio_segment_path in sorted(os.listdir("."))
        for match in [re.match(pattern, audio_segment_path)]
        if match and match.group(1)
    ]
