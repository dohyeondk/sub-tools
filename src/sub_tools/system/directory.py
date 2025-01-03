import os
import re


def change_directory(directory: str) -> None:
    """
    Changes the current working directory to the specified directory.
    """
    os.makedirs(directory, exist_ok=True)
    os.chdir(directory)
    os.makedirs("tmp", exist_ok=True)


def paths_with_offsets(
    prefix: str, file_format: str, directory: str = "."
) -> list[tuple[str, int]]:
    """
    Returns a list of paths with offsets.
    """
    pattern = rf"{prefix}_(\d+)\.{file_format}"
    return [
        (path, match.group(1))
        for path in sorted(os.listdir(directory))
        for match in [re.match(pattern, path)]
        if match and match.group(1)
    ]
