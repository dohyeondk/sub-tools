import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from sub_tools.config import config
from sub_tools.media.converter import download_from_url, video_to_audio

# A two-second synthetic clip (ffmpeg testsrc + sine tone) checked into the
# repository, so download tests never depend on a third-party file host. It is
# served over a local HTTP server below to keep the download path honest.
FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Test HLS/m3u8 stream URL; external, exercised only by the slow suite.
TEST_M3U8_URL = (
    "http://sample.vodobox.net/skate_phantom_flex_4k/skate_phantom_flex_4k.m3u8"
)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="module")
def fixture_server():
    """
    Serve tests/fixtures on a local port for the duration of the module.
    """
    handler = partial(QuietHandler, directory=str(FIXTURES_DIR))
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        yield f"http://127.0.0.1:{server.server_address[1]}"
        server.shutdown()


@pytest.fixture
def video_url(fixture_server):
    return f"{fixture_server}/video.mp4"


class TestDownloadFromUrl:
    """Integration tests for download_from_url using a locally served video."""

    def test_downloads_video_successfully(self, tmp_path, video_url):
        """Test successful video download over HTTP."""
        video_file = tmp_path / "test_video.mp4"

        config.url = video_url
        config.video_file = str(video_file)
        config.overwrite = True

        download_from_url()

        assert video_file.exists()
        assert video_file.stat().st_size > 0

    def test_skips_download_if_file_exists_and_no_overwrite(self, tmp_path, video_url):
        """Test that skips download if file exists and overwrite is False."""
        video_file = tmp_path / "existing_video.mp4"
        video_file.write_text("existing content")
        original_mtime = video_file.stat().st_mtime

        config.url = video_url
        config.video_file = str(video_file)
        config.overwrite = False

        download_from_url()

        assert video_file.read_text() == "existing content"
        assert video_file.stat().st_mtime == original_mtime

    def test_overwrites_existing_file_when_overwrite_true(self, tmp_path, video_url):
        """Test that overwrites existing file when overwrite is True."""
        video_file = tmp_path / "existing_video.mp4"
        video_file.write_text("existing content")

        config.url = video_url
        config.video_file = str(video_file)
        config.overwrite = True

        download_from_url()

        assert video_file.exists()
        assert video_file.stat().st_size > 100  # Much larger than "existing content"

    def test_raises_error_on_invalid_url(self, tmp_path, fixture_server):
        """Test that raises RuntimeError when the file does not exist."""
        video_file = tmp_path / "invalid.mp4"

        config.url = f"{fixture_server}/nonexistent-video-12345.mp4"
        config.video_file = str(video_file)
        config.overwrite = True

        with pytest.raises(RuntimeError, match="Failed to download media"):
            download_from_url()

    @pytest.mark.slow
    def test_downloads_hls_stream_successfully(self, tmp_path):
        """Test successful HLS/m3u8 stream download."""
        video_file = tmp_path / "test_hls_video.mp4"

        config.url = TEST_M3U8_URL
        config.video_file = str(video_file)
        config.overwrite = True

        download_from_url()

        assert video_file.exists()
        assert video_file.stat().st_size > 0


class TestVideoToAudio:
    """Integration tests for video_to_audio function."""

    def test_skips_conversion_if_audio_exists_and_no_overwrite(self, tmp_path, video_url):
        """Test that skips conversion if audio file exists and overwrite is False."""
        video_file = tmp_path / "test_video.mp4"
        audio_file = tmp_path / "existing_audio.mp3"

        config.url = video_url
        config.video_file = str(video_file)
        config.overwrite = True

        download_from_url()

        audio_file.write_text("existing audio content")
        original_mtime = audio_file.stat().st_mtime

        config.audio_file = str(audio_file)
        config.overwrite = False

        video_to_audio()

        assert audio_file.read_text() == "existing audio content"
        assert audio_file.stat().st_mtime == original_mtime
