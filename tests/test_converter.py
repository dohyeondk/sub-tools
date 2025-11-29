"""
Comprehensive tests for media converter utilities.
"""

import os
import subprocess
from unittest.mock import MagicMock, Mock, patch

import pytest

from sub_tools.media.converter import (
    download_from_url,
    media_to_signature,
    video_to_audio,
)


class TestDownloadFromUrl:
    """Tests for download_from_url function."""

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_downloads_video_successfully(self, mock_exists, mock_run):
        """Test successful video download."""
        mock_exists.return_value = False
        mock_run.return_value = Mock(returncode=0)

        url = "https://example.com/video.mp4"
        video_file = "output/video.mp4"

        download_from_url(url, video_file)

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "ffmpeg"
        assert args[1] == "-y"
        assert args[2] == "-i"
        assert args[3] == url
        assert args[-1] == video_file
        assert "-vn" not in args

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_downloads_audio_only(self, mock_exists, mock_run):
        """Test downloading audio only without video."""
        mock_exists.return_value = False
        mock_run.return_value = Mock(returncode=0)

        url = "https://example.com/audio.mp3"
        video_file = "output/audio.mp3"

        download_from_url(url, video_file, audio_only=True)

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "-vn" in args
        assert "-c:a" in args
        assert "libmp3lame" in args

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_skips_download_if_file_exists_and_no_overwrite(
        self, mock_exists, mock_run
    ):
        """Test that skips download if file exists and overwrite is False."""
        mock_exists.return_value = True

        url = "https://example.com/video.mp4"
        video_file = "output/video.mp4"

        download_from_url(url, video_file, overwrite=False)

        mock_run.assert_not_called()

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_overwrites_existing_file_when_overwrite_true(self, mock_exists, mock_run):
        """Test that overwrites existing file when overwrite is True."""
        mock_exists.return_value = True
        mock_run.return_value = Mock(returncode=0)

        url = "https://example.com/video.mp4"
        video_file = "output/video.mp4"

        download_from_url(url, video_file, overwrite=True)

        mock_run.assert_called_once()

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_raises_error_on_ffmpeg_failure(self, mock_exists, mock_run):
        """Test that raises RuntimeError when ffmpeg fails."""
        mock_exists.return_value = False
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "ffmpeg", stderr=b"Error: Invalid URL"
        )

        url = "https://example.com/invalid.mp4"
        video_file = "output/video.mp4"

        with pytest.raises(RuntimeError) as exc_info:
            download_from_url(url, video_file)

        assert "Failed to download media" in str(exc_info.value)
        assert url in str(exc_info.value)
        assert "Error: Invalid URL" in str(exc_info.value)

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_handles_ffmpeg_error_without_stderr(self, mock_exists, mock_run):
        """Test error handling when stderr is not available."""
        mock_exists.return_value = False
        error = subprocess.CalledProcessError(1, "ffmpeg")
        error.stderr = None
        mock_run.side_effect = error

        url = "https://example.com/video.mp4"
        video_file = "output/video.mp4"

        with pytest.raises(RuntimeError) as exc_info:
            download_from_url(url, video_file)

        assert "Failed to download media" in str(exc_info.value)

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_downloads_hls_stream(self, mock_exists, mock_run):
        """Test downloading HLS stream."""
        mock_exists.return_value = False
        mock_run.return_value = Mock(returncode=0)

        url = "https://example.com/playlist.m3u8"
        video_file = "output/video.mp4"

        download_from_url(url, video_file)

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[2] == "-i"
        assert args[3] == url

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_uses_check_true_for_subprocess(self, mock_exists, mock_run):
        """Test that subprocess.run is called with check=True."""
        mock_exists.return_value = False
        mock_run.return_value = Mock(returncode=0)

        url = "https://example.com/video.mp4"
        video_file = "output/video.mp4"

        download_from_url(url, video_file)

        assert mock_run.call_args[1]["check"] is True

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_captures_output(self, mock_exists, mock_run):
        """Test that subprocess output is captured."""
        mock_exists.return_value = False
        mock_run.return_value = Mock(returncode=0)

        url = "https://example.com/video.mp4"
        video_file = "output/video.mp4"

        download_from_url(url, video_file)

        assert mock_run.call_args[1]["capture_output"] is True

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_correct_ffmpeg_command_structure(self, mock_exists, mock_run):
        """Test that ffmpeg command has correct structure."""
        mock_exists.return_value = False
        mock_run.return_value = Mock(returncode=0)

        url = "https://example.com/video.mp4"
        video_file = "output/video.mp4"

        download_from_url(url, video_file)

        args = mock_run.call_args[0][0]
        # Check command structure: ffmpeg -y -i <url> <output>
        assert args[0] == "ffmpeg"
        assert args[1] == "-y"  # Overwrite flag
        assert args[2] == "-i"  # Input flag
        assert args[3] == url  # URL
        assert args[-1] == video_file  # Output file

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_audio_only_command_structure(self, mock_exists, mock_run):
        """Test audio-only command has correct codec parameters."""
        mock_exists.return_value = False
        mock_run.return_value = Mock(returncode=0)

        url = "https://example.com/audio.mp3"
        video_file = "output/audio.mp3"

        download_from_url(url, video_file, audio_only=True)

        args = mock_run.call_args[0][0]
        # Find indices of audio-specific flags
        vn_index = args.index("-vn")
        ca_index = args.index("-c:a")
        codec_index = args.index("libmp3lame")

        # Verify they appear in correct order and before output file
        assert vn_index < ca_index < codec_index
        assert codec_index < len(args) - 1


class TestVideoToAudio:
    """Tests for video_to_audio function."""

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_converts_video_to_audio_successfully(self, mock_exists, mock_run):
        """Test successful video to audio conversion."""
        mock_exists.return_value = False
        mock_run.return_value = Mock(returncode=0)

        video_file = "input/video.mp4"
        audio_file = "output/audio.mp3"

        video_to_audio(video_file, audio_file)

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "ffmpeg"
        assert args[2] == "-i"
        assert args[3] == video_file
        assert "-vn" in args
        assert "-c:a" in args
        assert "libmp3lame" in args
        assert args[-1] == audio_file

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_skips_conversion_if_audio_exists_and_no_overwrite(
        self, mock_exists, mock_run
    ):
        """Test that skips conversion if audio file exists and overwrite is False."""
        mock_exists.return_value = True

        video_file = "input/video.mp4"
        audio_file = "output/audio.mp3"

        video_to_audio(video_file, audio_file, overwrite=False)

        mock_run.assert_not_called()

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_overwrites_existing_audio_when_overwrite_true(self, mock_exists, mock_run):
        """Test that overwrites existing audio file when overwrite is True."""
        mock_exists.return_value = True
        mock_run.return_value = Mock(returncode=0)

        video_file = "input/video.mp4"
        audio_file = "output/audio.mp3"

        video_to_audio(video_file, audio_file, overwrite=True)

        mock_run.assert_called_once()

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_raises_error_on_conversion_failure(self, mock_exists, mock_run):
        """Test that raises RuntimeError when conversion fails."""
        mock_exists.return_value = False
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "ffmpeg", stderr=b"Error: Invalid video file"
        )

        video_file = "input/video.mp4"
        audio_file = "output/audio.mp3"

        with pytest.raises(RuntimeError) as exc_info:
            video_to_audio(video_file, audio_file)

        assert "Failed to convert video to audio" in str(exc_info.value)
        assert "Error: Invalid video file" in str(exc_info.value)


class TestMediaToSignature:
    """Tests for media_to_signature function."""

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_generates_signature_successfully(self, mock_exists, mock_run):
        """Test successful signature generation."""
        mock_exists.return_value = False
        mock_run.return_value = Mock(returncode=0)

        media_file = "output/audio.mp3"
        signature_file = "output/signature.shazamsignature"

        media_to_signature(media_file, signature_file)

        # Should be called twice: once to check shazam availability, once to generate
        assert mock_run.call_count == 2

        # Check signature generation call
        args = mock_run.call_args_list[1][0][0]
        assert args[0] == "shazam"
        assert args[1] == "signature"
        assert "--input" in args
        assert media_file in args
        assert "--output" in args
        assert signature_file in args

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_skips_if_signature_exists_and_no_overwrite(self, mock_exists, mock_run):
        """Test that skips signature generation if file exists and overwrite is False."""
        mock_exists.return_value = True

        media_file = "output/audio.mp3"
        signature_file = "output/signature.shazamsignature"

        media_to_signature(media_file, signature_file, overwrite=False)

        mock_run.assert_not_called()

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_overwrites_existing_signature_when_overwrite_true(
        self, mock_exists, mock_run
    ):
        """Test that overwrites existing signature when overwrite is True."""
        mock_exists.return_value = True
        mock_run.return_value = Mock(returncode=0)

        media_file = "output/audio.mp3"
        signature_file = "output/signature.shazamsignature"

        media_to_signature(media_file, signature_file, overwrite=True)

        assert mock_run.call_count == 2

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_skips_if_shazam_not_available(self, mock_exists, mock_run):
        """Test that skips signature generation if shazam CLI is not available."""
        mock_exists.return_value = False
        mock_run.side_effect = FileNotFoundError()

        media_file = "output/audio.mp3"
        signature_file = "output/signature.shazamsignature"

        # Should not raise, just skip
        media_to_signature(media_file, signature_file)

        # Only called once to check availability
        mock_run.assert_called_once()

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_skips_if_shazam_check_fails(self, mock_exists, mock_run):
        """Test that skips if shazam availability check fails."""
        mock_exists.return_value = False
        mock_run.side_effect = subprocess.SubprocessError()

        media_file = "output/audio.mp3"
        signature_file = "output/signature.shazamsignature"

        # Should not raise, just skip
        media_to_signature(media_file, signature_file)

        mock_run.assert_called_once()

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_raises_error_on_signature_generation_failure(self, mock_exists, mock_run):
        """Test that raises RuntimeError when signature generation fails."""
        mock_exists.return_value = False

        # First call succeeds (shazam check), second fails (signature generation)
        mock_run.side_effect = [
            Mock(returncode=0),
            subprocess.CalledProcessError(
                1, "shazam", stderr=b"Error: Invalid media file"
            ),
        ]

        media_file = "output/audio.mp3"
        signature_file = "output/signature.shazamsignature"

        with pytest.raises(RuntimeError) as exc_info:
            media_to_signature(media_file, signature_file)

        assert "Failed to generate signature" in str(exc_info.value)
        assert "Error: Invalid media file" in str(exc_info.value)

    @patch("sub_tools.media.converter.subprocess.run")
    @patch("sub_tools.media.converter.os.path.exists")
    def test_correct_shazam_command_structure(self, mock_exists, mock_run):
        """Test that shazam command has correct structure."""
        mock_exists.return_value = False
        mock_run.return_value = Mock(returncode=0)

        media_file = "output/audio.mp3"
        signature_file = "output/signature.shazamsignature"

        media_to_signature(media_file, signature_file)

        # Get the signature generation call (second call)
        args = mock_run.call_args_list[1][0][0]

        assert args == [
            "shazam",
            "signature",
            "--input",
            media_file,
            "--output",
            signature_file,
        ]
