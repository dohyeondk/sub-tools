"""
Integration tests for media converter utilities using real test videos.
"""

import os
import pytest
from sub_tools.media.converter import download_from_url, video_to_audio

# Test video URL - 10 second Big Buck Bunny sample (1MB)
TEST_VIDEO_URL = "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"

# Test HLS/m3u8 stream URL
TEST_M3U8_URL = "http://cdnbakmi.kaltura.com/p/243342/sp/24334200/playManifest/entryId/0_uka1msg4/flavorIds/1_vqhfu6uy,1_80sohj7p/format/applehttp/protocol/http/a.m3u8"


class TestDownloadFromUrl:
    """Integration tests for download_from_url function using real video."""

    def test_downloads_video_successfully(self, tmp_path):
        """Test successful video download from real URL."""
        video_file = tmp_path / "test_video.mp4"
        download_from_url(TEST_VIDEO_URL, video_file)

        assert video_file.exists()
        assert video_file.stat().st_size > 0

    def test_skips_download_if_file_exists_and_no_overwrite(self, tmp_path):
        """Test that skips download if file exists and overwrite is False."""
        video_file = tmp_path / "existing_video.mp4"
        video_file.write_text("existing content")
        original_mtime = video_file.stat().st_mtime

        download_from_url(TEST_VIDEO_URL, str(video_file), overwrite=False)

        assert video_file.read_text() == "existing content"
        assert video_file.stat().st_mtime == original_mtime

    def test_overwrites_existing_file_when_overwrite_true(self, tmp_path):
        """Test that overwrites existing file when overwrite is True."""
        video_file = tmp_path / "existing_video.mp4"
        video_file.write_text("existing content")

        download_from_url(TEST_VIDEO_URL, str(video_file), overwrite=True)

        assert video_file.exists()
        assert video_file.stat().st_size > 100  # Much larger than "existing content"

    def test_raises_error_on_invalid_url(self, tmp_path):
        """Test that raises RuntimeError for invalid URL."""
        video_file = tmp_path / "invalid.mp4"
        invalid_url = "https://example.com/nonexistent-video-12345.mp4"

        with pytest.raises(RuntimeError, match="Failed to download media"):
            download_from_url(invalid_url, str(video_file))

    @pytest.mark.slow
    def test_downloads_hls_stream_successfully(self, tmp_path):
        """Test successful HLS/m3u8 stream download."""
        video_file = tmp_path / "test_hls_video.mp4"
        download_from_url(TEST_M3U8_URL, str(video_file))

        assert video_file.exists()
        assert video_file.stat().st_size > 0


class TestVideoToAudio:
    """Integration tests for video_to_audio function."""

    def test_skips_conversion_if_audio_exists_and_no_overwrite(self, tmp_path):
        """Test that skips conversion if audio file exists and overwrite is False."""
        video_file = tmp_path / "test_video.mp4"
        audio_file = tmp_path / "existing_audio.mp3"

        # Download test video first
        download_from_url(TEST_VIDEO_URL, str(video_file))

        audio_file.write_text("existing audio content")
        original_mtime = audio_file.stat().st_mtime

        video_to_audio(str(video_file), str(audio_file), overwrite=False)

        assert audio_file.read_text() == "existing audio content"
        assert audio_file.stat().st_mtime == original_mtime
