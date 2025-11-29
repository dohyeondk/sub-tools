"""
Integration tests for media converter utilities using real test videos.
"""

import os
import shutil
import tempfile

import pytest

from sub_tools.media.converter import download_from_url, video_to_audio

# Test video URL - 10 second Big Buck Bunny sample (1MB)
TEST_VIDEO_URL = "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    temp_dir = tempfile.mkdtemp(prefix="sub_tools_test_")
    yield temp_dir
    # Cleanup after test
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


class TestDownloadFromUrl:
    """Integration tests for download_from_url function using real video."""

    def test_downloads_video_successfully(self, temp_output_dir):
        """Test successful video download from real URL."""
        video_file = os.path.join(temp_output_dir, "test_video.mp4")

        download_from_url(TEST_VIDEO_URL, video_file)

        # Verify file was created and has content
        assert os.path.exists(video_file)
        assert os.path.getsize(video_file) > 0

    def test_skips_download_if_file_exists_and_no_overwrite(self, temp_output_dir):
        """Test that skips download if file exists and overwrite is False."""
        video_file = os.path.join(temp_output_dir, "existing_video.mp4")

        # Create existing file
        with open(video_file, "w") as f:
            f.write("existing content")
        original_size = os.path.getsize(video_file)

        # Try to download without overwrite
        download_from_url(TEST_VIDEO_URL, video_file, overwrite=False)

        # File should remain unchanged
        assert os.path.getsize(video_file) == original_size
        with open(video_file, "r") as f:
            assert f.read() == "existing content"

    def test_overwrites_existing_file_when_overwrite_true(self, temp_output_dir):
        """Test that overwrites existing file when overwrite is True."""
        video_file = os.path.join(temp_output_dir, "existing_video.mp4")

        # Create existing file
        with open(video_file, "w") as f:
            f.write("existing content")

        # Download with overwrite
        download_from_url(TEST_VIDEO_URL, video_file, overwrite=True)

        # File should be replaced with actual video
        assert os.path.exists(video_file)
        assert os.path.getsize(video_file) > 100  # Much larger than "existing content"

    def test_raises_error_on_invalid_url(self, temp_output_dir):
        """Test that raises RuntimeError for invalid URL."""
        video_file = os.path.join(temp_output_dir, "invalid.mp4")
        invalid_url = "https://example.com/nonexistent-video-12345.mp4"

        with pytest.raises(RuntimeError) as exc_info:
            download_from_url(invalid_url, video_file)

        assert "Failed to download media" in str(exc_info.value)


class TestVideoToAudio:
    """Integration tests for video_to_audio function."""

    def test_skips_conversion_if_audio_exists_and_no_overwrite(self, temp_output_dir):
        """Test that skips conversion if audio file exists and overwrite is False."""
        video_file = os.path.join(temp_output_dir, "test_video.mp4")
        audio_file = os.path.join(temp_output_dir, "existing_audio.mp3")

        # Download test video
        download_from_url(TEST_VIDEO_URL, video_file)

        # Create existing audio file
        with open(audio_file, "w") as f:
            f.write("existing audio content")
        original_size = os.path.getsize(audio_file)

        # Try to convert without overwrite
        video_to_audio(video_file, audio_file, overwrite=False)

        # File should remain unchanged
        assert os.path.getsize(audio_file) == original_size
        with open(audio_file, "r") as f:
            assert f.read() == "existing audio content"
