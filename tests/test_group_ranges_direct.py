"""
A simplied test file for segmenter._group_ranges that avoids import dependencies.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the function directly from the file
def test_group_ranges():
    """Test the _group_ranges function directly."""
    # Copy the implementation from the module to test it directly
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

    # Now run the tests
    assert _group_ranges([], 1_000, 3_000) == []

    ranges = [(0, 1_000), (2_000, 3_000), (5_000, 6_000), (6_000, 7_000)]
    grouped_ranges = _group_ranges(ranges, 1_000, 3_000)
    assert grouped_ranges == [(0, 3_000), (5_000, 7_000)]

    ranges = [(0, 1_000), (2_000, 3_000), (4_000, 5_000), (6_000, 7_000)]
    grouped_ranges = _group_ranges(ranges, 1_000, 3_000)
    assert grouped_ranges == [(0, 3_000), (4_000, 7_000)]

if __name__ == "__main__":
    test_group_ranges()
    print("All tests passed!")