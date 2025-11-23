import os
import shutil
import tempfile

import pytest

from sub_tools.config import Config
from sub_tools.media.segmenter import _group_ranges, segment_audio
from sub_tools.system.directory import get_temp_directory


@pytest.fixture
def sample_audio():
    return "tests/data/sample.mp3"


def test_segment_audio(sample_audio):
    # Use test-specific temp directory
    test_temp = get_temp_directory(subfolder="test-sub-tools")
    shutil.rmtree(test_temp, ignore_errors=True)
    os.makedirs(test_temp, exist_ok=True)

    segment_audio(
        sample_audio,
        "sample_segments",
        "wav",
        60_000,
        config=Config(directory=test_temp),
    )
    num_files = len(os.listdir(test_temp))
    shutil.rmtree(test_temp)
    assert num_files == 11


def test_group_ranges():
    assert _group_ranges([], 1_000, 3_000) == []

    ranges = [(0, 1_000), (2_000, 3_000), (5_000, 6_000), (6_000, 7_000)]
    grouped_ranges = _group_ranges(ranges, 1_000, 3_000)
    assert grouped_ranges == [(0, 3_000), (5_000, 7_000)]

    ranges = [(0, 1_000), (2_000, 3_000), (4_000, 5_000), (6_000, 7_000)]
    grouped_ranges = _group_ranges(ranges, 1_000, 3_000)
    assert grouped_ranges == [(0, 3_000), (4_000, 7_000)]
