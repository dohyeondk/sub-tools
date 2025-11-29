"""
Directory and temporary file management utilities.
"""

import hashlib
import os
import tempfile


def ensure_output_directory() -> None:
    """
    Ensures the output directory exists for final output files.
    """
    os.makedirs("output", exist_ok=True)


def get_url_hash(url: str) -> str:
    """
    Generate a SHA-256 hash from a URL for use as a directory name.

    Args:
        url: The URL to hash

    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(url.encode()).hexdigest()


def get_temp_directory(url: str | None = None, subfolder: str = "sub-tools") -> str:
    """
    Get the temporary directory path for the application.

    If a URL is provided, creates a hash-based subdirectory for caching.
    Otherwise, creates a generic temp directory.

    Args:
        url: Optional URL to create hash-based subdirectory
        subfolder: Base subfolder name in system temp (default: "sub-tools")

    Returns:
        Path to the temporary directory
    """
    base_temp = tempfile.gettempdir()
    temp_path = os.path.join(base_temp, subfolder)

    if url:
        url_hash = get_url_hash(url)
        temp_path = os.path.join(temp_path, url_hash)

    os.makedirs(temp_path, exist_ok=True)
    return temp_path


def cache_exists(url: str | None, filename: str, subfolder: str = "sub-tools") -> bool:
    """
    Check if a cached file exists for a given URL.

    Args:
        url: The URL to check cache for, or None
        filename: The filename to check in the cache
        subfolder: Base subfolder name in system temp (default: "sub-tools")

    Returns:
        True if the cached file exists, False otherwise
    """
    temp_dir = get_temp_directory(url, subfolder)
    file_path = os.path.join(temp_dir, filename)
    return os.path.exists(file_path)


def get_cached_file_path(
    url: str | None, filename: str, subfolder: str = "sub-tools"
) -> str:
    """
    Get the full path to a cached file for a given URL.

    Args:
        url: The URL to get cache path for, or None
        filename: The filename in the cache
        subfolder: Base subfolder name in system temp (default: "sub-tools")

    Returns:
        Full path to the cached file
    """
    temp_dir = get_temp_directory(url, subfolder)
    return os.path.join(temp_dir, filename)
