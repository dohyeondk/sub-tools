import os
import shutil

import pytest

from sub_tools.media.segmenter import _group_ranges, segment_audio


@pytest.fixture
def sample_audio():
    return "tests/data/sample.mp3"


def test_segment_audio(sample_audio):
    shutil.rmtree("tmp", ignore_errors=True)
    os.makedirs("tmp", exist_ok=True)
    segment_audio(sample_audio, "sample_segments", "wav", 60_000)
    num_files = len(os.listdir("tmp"))
    shutil.rmtree("tmp")
    assert num_files == 11


def test_group_ranges():
    assert _group_ranges([], 1_000, 3_000) == []

    ranges = [(0, 1_000), (2_000, 3_000), (5_000, 6_000), (6_000, 7_000)]
    grouped_ranges = _group_ranges(ranges, 1_000, 3_000)
    assert grouped_ranges == [(0, 3_000), (5_000, 7_000)]

    ranges = [(0, 1_000), (2_000, 3_000), (4_000, 5_000), (6_000, 7_000)]
    grouped_ranges = _group_ranges(ranges, 1_000, 3_000)
    assert grouped_ranges == [(0, 3_000), (4_000, 7_000)]
