import os

from ..config import config
from .console import warning


def ensure_output_directory(path: str) -> None:
    """
    Ensures the output directory exists and changes to it.
    """
    os.makedirs(path, exist_ok=True)
    os.chdir(path)


def should_skip(file: str) -> bool:
    """
    Checks if a file should be skipped based on existence and overwrite flag.
    """
    if os.path.exists(file) and not config.overwrite:
        path = os.path.join(config.output_directory, file)
        warning(f"File {path} already exists. Skipping...")
        return True
    return False
