import os
import shutil
import pytest

from pydub import AudioSegment
from sub_tools.media.segmenter import SegmentConfig, _get_segment_ranges, _find_split_point, segment_audio


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
        min_silence_length=500,
        silence_threshold_db=16,
        search_window_ratio=0.1
    )
    
    # Test with 5-second segments
    ranges = _get_segment_ranges(sample_audio, 10_000, config)
    assert len(ranges) == 6
    assert ranges[0][0] == 0  # First segment should start at 0
    assert ranges[-1][1] == len(sample_audio)  # Last segment should end at total length


def test_find_split_point(sample_audio):
    config = SegmentConfig(
        min_silence_length=500,
        silence_threshold_db=16,
        search_window_ratio=0.1
    )
    
    # Test finding split point in the middle silence
    split_point = _find_split_point(sample_audio, 5_000, 15_000, config)
    assert split_point is not None
    assert 8_000 <= split_point <= 10_000  # Split should be found in the silence
