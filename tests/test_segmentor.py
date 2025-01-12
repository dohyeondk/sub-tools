import os
import shutil
import pytest

from pydub import AudioSegment
from sub_tools.media.segmenter import SegmentConfig, _get_segment_ranges, _find_split_range, segment_audio, _filter_ranges

@pytest.fixture
def sample_audio():
    # 0s        10s        20s        30s        40s        50s        60s
    # |-------|--|-------|--|-------|--|-------|--|-------|--|-------|--|
    #     8s   2s    8s   2s    8s   2s    8s   2s    8s   2s    8s   2s
    #   audio      audio      audio      audio      audio      audio
    return AudioSegment.from_file("tests/data/sample.mp3")


def test_segment_audio(sample_audio):
    os.makedirs("tmp", exist_ok=True)
    segment_audio("tests/data/sample.mp3", "sample_segments", "mp3", 10_000)
    assert len(os.listdir("tmp")) == 6
    shutil.rmtree("tmp")


def test_get_segment_ranges(sample_audio):
    config = SegmentConfig(
        silence_threshold_db=-64,
        seek_step=10,
    )
    
    ranges = _get_segment_ranges(sample_audio, 10_000, config)
    assert len(ranges) == 6
    assert ranges[0] == (0, 8_000)
    assert ranges[1] == (10_050, 18_000)
    assert ranges[2] == (20_050, 28_000)
    assert ranges[3] == (30_050, 38_000)
    assert ranges[4] == (40_050, 48_000)
    assert ranges[5] == (50_050, 58_000)


def test_find_split_range(sample_audio):
    config = SegmentConfig(
        max_silence_length=500,
        silence_threshold_db=-64,
        seek_step=10,
    )
    
    split_range = _find_split_range(sample_audio, 0, 10_000, config)
    assert split_range == (0, 8_000)

    split_range = _find_split_range(sample_audio, 0, 20_000, config)
    assert split_range == (0, 8_000)

    split_range = _find_split_range(sample_audio, 10_000, 20_000, config)
    assert split_range == (10_000, 18_000)

    split_range = _find_split_range(sample_audio, 58_000, 58_018, config)
    assert split_range == (58_000, 58_018)


def test_filter_ranges():
    # No ranges
    ranges = []
    filtered_ranges = _filter_ranges(ranges, 1000)
    assert filtered_ranges == []

    # Single range
    ranges = [(0, 1000)]
    filtered_ranges = _filter_ranges(ranges, 1000)
    assert filtered_ranges == [(0, 1000)]

    # Silent range is less than max_silence_length
    ranges = [(0, 1000), (2000, 3000), (4000, 6000), (6000, 7000)]
    filtered_ranges = _filter_ranges(ranges, 1000)
    assert filtered_ranges == [(0, 1000), (2000, 3000), (4000, 6000), (6000, 7000)]

    # Silence length is greater than max_silence_length
    ranges = [(0, 1000), (2000, 3000), (5000, 6000), (6000, 7000)]
    filtered_ranges = _filter_ranges(ranges, 1000)
    assert filtered_ranges == [(0, 1000), (2000, 3000)]
