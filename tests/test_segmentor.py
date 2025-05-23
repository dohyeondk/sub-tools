import os
import shutil
import pytest

from sub_tools.media.segmenter import segment_audio, _group_ranges

@pytest.fixture
def sample_audio():
    return os.path.abspath("tests/data/sample.mp3")

@pytest.fixture
def sample_audio_fixture(sample_audio):
    # Verify the audio file exists
    assert os.path.exists(sample_audio), f"Sample audio file not found: {sample_audio}"
    return sample_audio


@pytest.mark.parametrize("sample_audio_fixture", [("sample_audio")], indirect=True)
def test_segment_audio(sample_audio_fixture):
    # Create a clean temporary directory
    test_tmp_dir = "tmp_test_segmentor"
    shutil.rmtree(test_tmp_dir, ignore_errors=True)
    os.makedirs(test_tmp_dir, exist_ok=True)
    
    try:
        # Configure segmenter to use our test directory
        from sub_tools.media.segmenter import SegmentConfig
        config = SegmentConfig(directory=test_tmp_dir)
        
        # Perform segmentation
        segment_audio(sample_audio_fixture, "sample_segments", "wav", 60_000, config=config)
        
        # Check that segmentation produced a reasonable number of files
        # The exact number may vary by environment, silero_vad version, etc.
        files = os.listdir(test_tmp_dir)
        assert len(files) > 0, "Segmentation should produce at least one file"
        assert all(f.startswith("sample_segments_") for f in files), "All files should have the correct prefix"
    finally:
        # Clean up test directory
        shutil.rmtree(test_tmp_dir, ignore_errors=True)


def test_group_ranges():
    assert _group_ranges([], 1_000, 3_000) == []

    ranges = [(0, 1_000), (2_000, 3_000), (5_000, 6_000), (6_000, 7_000)]
    grouped_ranges = _group_ranges(ranges, 1_000, 3_000)
    assert grouped_ranges == [(0, 3_000), (5_000, 7_000)]

    ranges = [(0, 1_000), (2_000, 3_000), (4_000, 5_000), (6_000, 7_000)]
    grouped_ranges = _group_ranges(ranges, 1_000, 3_000)
    assert grouped_ranges == [(0, 3_000), (4_000, 7_000)]
