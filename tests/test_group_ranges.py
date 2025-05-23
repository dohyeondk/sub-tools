import pytest

def _group_ranges(
    ranges: list[tuple[int, int]],
    max_silence_length: int,
    max_segment_length: int,
) -> list[tuple[int, int]]:
    """
    Combines ranges that are within max_silence_length of each other.
    """
    if not ranges:
        return []

    grouped = [ranges[0]]
    for curr in ranges[1:]:
        if curr[0] - grouped[-1][1] <= max_silence_length and curr[1] - grouped[-1][0] <= max_segment_length:
            grouped[-1] = (grouped[-1][0], curr[1])
        else:
            grouped.append(curr)

    return grouped

def test_group_ranges():
    assert _group_ranges([], 1_000, 3_000) == []

    ranges = [(0, 1_000), (2_000, 3_000), (5_000, 6_000), (6_000, 7_000)]
    grouped_ranges = _group_ranges(ranges, 1_000, 3_000)
    assert grouped_ranges == [(0, 3_000), (5_000, 7_000)]

    ranges = [(0, 1_000), (2_000, 3_000), (4_000, 5_000), (6_000, 7_000)]
    grouped_ranges = _group_ranges(ranges, 1_000, 3_000)
    assert grouped_ranges == [(0, 3_000), (4_000, 7_000)]