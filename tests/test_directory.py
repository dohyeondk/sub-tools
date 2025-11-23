"""
Comprehensive tests for directory management utilities.
"""

import os
import shutil
import tempfile

import pytest

from sub_tools.system.directory import (
    cache_exists,
    ensure_output_directory,
    get_cached_file_path,
    get_temp_directory,
    get_url_hash,
    paths_with_offsets,
)


class TestEnsureOutputDirectory:
    """Tests for ensure_output_directory function."""

    def test_creates_output_directory(self, tmp_path):
        """Test that output directory is created."""
        # Change to temp directory for testing
        original_dir = os.getcwd()
        os.chdir(tmp_path)

        try:
            ensure_output_directory()
            assert os.path.exists("output")
            assert os.path.isdir("output")
        finally:
            os.chdir(original_dir)

    def test_does_not_fail_if_exists(self, tmp_path):
        """Test that function doesn't fail if directory already exists."""
        original_dir = os.getcwd()
        os.chdir(tmp_path)

        try:
            os.makedirs("output")
            ensure_output_directory()  # Should not raise
            assert os.path.exists("output")
        finally:
            os.chdir(original_dir)


class TestGetUrlHash:
    """Tests for get_url_hash function."""

    def test_generates_correct_sha256_hash(self):
        """Test that generates correct SHA-256 hash for known input."""
        url = "https://example.com/video.mp4"
        expected_hash = (
            "da09b2ab4d33db12c2f8ecb9449572e139891ed2b22091aecc863bc85e2dc936"
        )
        hash_value = get_url_hash(url)
        assert hash_value == expected_hash

    def test_hash_is_deterministic(self):
        """Test that same URL produces same hash."""
        url = "https://example.com/video.mp4"
        hash1 = get_url_hash(url)
        hash2 = get_url_hash(url)
        assert hash1 == hash2
        assert (
            hash1 == "da09b2ab4d33db12c2f8ecb9449572e139891ed2b22091aecc863bc85e2dc936"
        )

    def test_different_urls_produce_different_hashes(self):
        """Test that different URLs produce different hashes."""
        url1 = "https://example.com/video1.mp4"
        url2 = "https://example.com/video2.mp4"
        hash1 = get_url_hash(url1)
        hash2 = get_url_hash(url2)
        assert (
            hash1 == "c14c56c4f25cbfc2b87d39d20f85f80392da9512bf88a7fa15a23a2c9aeb28ef"
        )
        assert (
            hash2 == "37c225b7ef81a38b58c52a224dd2de34880e009df208d276bcbbdd4efc5bf9d5"
        )
        assert hash1 != hash2

    def test_handles_special_characters(self):
        """Test hash generation with special characters in URL."""
        url = "https://example.com/video?id=123&lang=en"
        expected_hash = (
            "e911435f93c6cac6a5c564faec87ac8aaa7c3b8cc05e97c090d253c6cf6ade7c"
        )
        hash_value = get_url_hash(url)
        assert hash_value == expected_hash

    def test_handles_unicode(self):
        """Test hash generation with unicode characters."""
        url = "https://example.com/视频.mp4"
        expected_hash = (
            "ba3322efbef02c42434b7eb65a6795c1d92dc3e821fe399050095ced0284634b"
        )
        hash_value = get_url_hash(url)
        assert hash_value == expected_hash


class TestGetTempDirectory:
    """Tests for get_temp_directory function."""

    def test_creates_generic_temp_directory(self):
        """Test temp directory creation without URL."""
        temp_dir = get_temp_directory(url=None, subfolder="test-sub-tools")

        assert temp_dir.startswith(tempfile.gettempdir())
        assert "test-sub-tools" in temp_dir
        assert os.path.exists(temp_dir)
        assert os.path.isdir(temp_dir)

        # Cleanup
        os.rmdir(temp_dir)

    def test_creates_url_based_temp_directory(self):
        """Test temp directory creation with URL hash."""
        url = "https://example.com/test-video.mp4"
        temp_dir = get_temp_directory(url=url, subfolder="test-sub-tools")

        assert temp_dir.startswith(tempfile.gettempdir())
        assert "test-sub-tools" in temp_dir
        assert get_url_hash(url) in temp_dir
        assert os.path.exists(temp_dir)
        assert os.path.isdir(temp_dir)

        # Cleanup
        os.rmdir(temp_dir)

    def test_same_url_returns_same_directory(self):
        """Test that same URL returns same directory path."""
        url = "https://example.com/same-video.mp4"
        temp_dir1 = get_temp_directory(url=url, subfolder="test-sub-tools")
        temp_dir2 = get_temp_directory(url=url, subfolder="test-sub-tools")

        assert temp_dir1 == temp_dir2

        # Cleanup
        os.rmdir(temp_dir1)

    def test_different_urls_return_different_directories(self):
        """Test that different URLs return different directories."""
        url1 = "https://example.com/video1.mp4"
        url2 = "https://example.com/video2.mp4"
        temp_dir1 = get_temp_directory(url=url1, subfolder="test-sub-tools")
        temp_dir2 = get_temp_directory(url=url2, subfolder="test-sub-tools")

        assert temp_dir1 != temp_dir2

        # Cleanup
        os.rmdir(temp_dir1)
        os.rmdir(temp_dir2)

    def test_custom_subfolder(self):
        """Test using custom subfolder name."""
        temp_dir = get_temp_directory(url=None, subfolder="custom-folder")
        assert "custom-folder" in temp_dir

        # Cleanup
        os.rmdir(temp_dir)


class TestCacheExists:
    """Tests for cache_exists function."""

    def test_returns_false_when_cache_does_not_exist(self):
        """Test that returns False when cached file doesn't exist."""
        url = "https://example.com/cache-test-1.mp4"
        filename = "nonexistent.txt"

        assert not cache_exists(url, filename, subfolder="test-sub-tools")

        # Cleanup
        temp_dir = get_temp_directory(url, subfolder="test-sub-tools")
        os.rmdir(temp_dir)

    def test_returns_true_when_cache_exists(self):
        """Test that returns True when cached file exists."""
        url = "https://example.com/cache-test-2.mp4"
        filename = "cached_file.txt"

        # Create cached file
        temp_dir = get_temp_directory(url, subfolder="test-sub-tools")
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, "w") as f:
            f.write("test content")

        assert cache_exists(url, filename, subfolder="test-sub-tools")

        # Cleanup
        os.remove(file_path)
        os.rmdir(temp_dir)

    def test_checks_correct_directory(self):
        """Test that checks in the correct URL-specific directory."""
        url1 = "https://example.com/video1.mp4"
        url2 = "https://example.com/video2.mp4"
        filename = "test.txt"

        # Create file in url1's cache
        temp_dir1 = get_temp_directory(url1, subfolder="test-sub-tools")
        file_path1 = os.path.join(temp_dir1, filename)
        with open(file_path1, "w") as f:
            f.write("content")

        # Should exist for url1
        assert cache_exists(url1, filename, subfolder="test-sub-tools")
        # Should not exist for url2
        assert not cache_exists(url2, filename, subfolder="test-sub-tools")

        # Cleanup
        os.remove(file_path1)
        os.rmdir(temp_dir1)
        temp_dir2 = get_temp_directory(url2, subfolder="test-sub-tools")
        os.rmdir(temp_dir2)

    def test_works_with_none_url(self):
        """Test that works with None URL (generic temp directory)."""
        filename = "test_none.txt"

        # Create file in generic cache
        temp_dir = get_temp_directory(None, subfolder="test-sub-tools-none")
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, "w") as f:
            f.write("content")

        # Should exist
        assert cache_exists(None, filename, subfolder="test-sub-tools-none")

        # Cleanup
        os.remove(file_path)
        os.rmdir(temp_dir)


class TestGetCachedFilePath:
    """Tests for get_cached_file_path function."""

    def test_returns_correct_path(self):
        """Test that returns correct file path."""
        url = "https://example.com/path-test.mp4"
        filename = "video.mp4"

        file_path = get_cached_file_path(url, filename, subfolder="test-sub-tools")

        assert tempfile.gettempdir() in file_path
        assert "test-sub-tools" in file_path
        assert get_url_hash(url) in file_path
        assert filename in file_path

        # Cleanup
        temp_dir = os.path.dirname(file_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

    def test_same_url_same_filename_returns_same_path(self):
        """Test that same inputs return same path."""
        url = "https://example.com/same.mp4"
        filename = "file.mp4"

        path1 = get_cached_file_path(url, filename, subfolder="test-sub-tools")
        path2 = get_cached_file_path(url, filename, subfolder="test-sub-tools")

        assert path1 == path2

        # Cleanup
        temp_dir = os.path.dirname(path1)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

    def test_works_with_none_url(self):
        """Test that works with None URL (generic temp directory)."""
        filename = "generic_file.mp4"

        file_path = get_cached_file_path(
            None, filename, subfolder="test-sub-tools-none"
        )

        assert tempfile.gettempdir() in file_path
        assert "test-sub-tools-none" in file_path
        assert filename in file_path

        # Cleanup
        temp_dir = os.path.dirname(file_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)


class TestPathsWithOffsets:
    """Tests for paths_with_offsets function."""

    def test_returns_empty_list_for_empty_directory(self, tmp_path):
        """Test that returns empty list when no matching files."""
        result = paths_with_offsets("prefix", "mp3", str(tmp_path))
        assert result == []

    def test_finds_files_with_offsets(self, tmp_path):
        """Test that finds files with numeric offsets."""
        # Create test files
        (tmp_path / "audio_0.mp3").touch()
        (tmp_path / "audio_5000.mp3").touch()
        (tmp_path / "audio_10000.mp3").touch()

        result = paths_with_offsets("audio", "mp3", str(tmp_path))

        assert len(result) == 3
        assert ("audio_0.mp3", 0) in result
        assert ("audio_5000.mp3", 5000) in result
        assert ("audio_10000.mp3", 10000) in result

    def test_returns_sorted_list(self, tmp_path):
        """Test that returns files in sorted order by numeric offset."""
        # Create files in random order
        (tmp_path / "seg_10000.wav").touch()
        (tmp_path / "seg_0.wav").touch()
        (tmp_path / "seg_5000.wav").touch()

        result = paths_with_offsets("seg", "wav", str(tmp_path))

        # Should be sorted numerically by offset, not alphabetically
        assert result[0] == ("seg_0.wav", 0)
        assert result[1] == ("seg_5000.wav", 5000)
        assert result[2] == ("seg_10000.wav", 10000)

    def test_ignores_non_matching_files(self, tmp_path):
        """Test that ignores files that don't match pattern."""
        (tmp_path / "audio_0.mp3").touch()
        (tmp_path / "audio_5000.mp3").touch()
        (tmp_path / "other_file.mp3").touch()
        (tmp_path / "audio.mp3").touch()
        (tmp_path / "audio_abc.mp3").touch()

        result = paths_with_offsets("audio", "mp3", str(tmp_path))

        assert len(result) == 2
        assert all("audio_" in path for path, _ in result)

    def test_matches_different_prefixes(self, tmp_path):
        """Test matching with different prefixes."""
        (tmp_path / "video_0.mp4").touch()
        (tmp_path / "audio_0.mp3").touch()

        video_result = paths_with_offsets("video", "mp4", str(tmp_path))
        audio_result = paths_with_offsets("audio", "mp3", str(tmp_path))

        assert len(video_result) == 1
        assert len(audio_result) == 1
        assert video_result[0][0] == "video_0.mp4"
        assert audio_result[0][0] == "audio_0.mp3"

    def test_matches_different_formats(self, tmp_path):
        """Test matching with different file formats."""
        (tmp_path / "seg_0.mp3").touch()
        (tmp_path / "seg_0.wav").touch()
        (tmp_path / "seg_0.srt").touch()

        mp3_result = paths_with_offsets("seg", "mp3", str(tmp_path))
        wav_result = paths_with_offsets("seg", "wav", str(tmp_path))
        srt_result = paths_with_offsets("seg", "srt", str(tmp_path))

        assert len(mp3_result) == 1
        assert len(wav_result) == 1
        assert len(srt_result) == 1

    def test_handles_large_offsets(self, tmp_path):
        """Test handling of large offset numbers."""
        (tmp_path / "seg_999999999.mp3").touch()

        result = paths_with_offsets("seg", "mp3", str(tmp_path))

        assert len(result) == 1
        assert result[0][1] == 999999999

    def test_uses_current_directory_by_default(self):
        """Test that uses current directory when no directory specified."""
        original_dir = os.getcwd()
        temp_dir = tempfile.mkdtemp()

        try:
            os.chdir(temp_dir)
            # Create test file
            with open("test_0.txt", "w") as f:
                f.write("test")

            result = paths_with_offsets("test", "txt")
            assert len(result) == 1
            assert result[0][0] == "test_0.txt"

        finally:
            os.chdir(original_dir)
            shutil.rmtree(temp_dir)

    def test_offset_as_int(self, tmp_path):
        """Test that offset is returned as int for proper numeric sorting."""
        (tmp_path / "audio_12345.mp3").touch()

        result = paths_with_offsets("audio", "mp3", str(tmp_path))

        assert len(result) == 1
        path, offset = result[0]
        assert isinstance(offset, int)
        assert offset == 12345
