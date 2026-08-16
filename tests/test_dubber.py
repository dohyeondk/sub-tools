"""
The dub task's timing decisions, tested without ffmpeg or an API key.
"""

from sub_tools.media.dubber import (
    atempo_filter,
    cue_slots,
    plan_gaps,
    speakable_text,
)


class TestSpeakableText:
    def test_plain_text_is_kept(self):
        assert speakable_text("Hello there.") == "Hello there."

    def test_sound_effects_are_dropped(self):
        assert speakable_text("[door slams]") == ""

    def test_sound_effect_inside_a_line_is_removed(self):
        assert speakable_text("Wait... [gunshot] get down!") == "Wait... get down!"

    def test_parenthetical_directions_are_removed(self):
        assert speakable_text("(whispering) Come here") == "Come here"

    def test_multiline_cues_become_one_line(self):
        assert speakable_text("First line\nsecond line") == "First line second line"


class TestCueSlots:
    def test_slot_runs_to_the_next_cue(self):
        assert cue_slots([0.0, 4.0, 10.0], total_duration=12.0) == [4.0, 6.0, 2.0]

    def test_last_slot_is_unlimited_without_a_duration(self):
        assert cue_slots([0.0, 4.0], total_duration=None) == [4.0, None]

    def test_cues_sharing_a_start_get_no_slot(self):
        assert cue_slots([4.0, 4.0], total_duration=10.0) == [0.0, 6.0]


class TestPlanGaps:
    def test_segments_are_placed_at_their_start_times(self):
        gaps, pad = plan_gaps([1.0, 5.0], [2.0, 1.0], total_duration=10.0)
        assert gaps == [1.0, 2.0]
        assert pad == 4.0

    def test_overrunning_speech_pushes_the_next_segment(self):
        gaps, pad = plan_gaps([0.0, 2.0], [3.0, 1.0], total_duration=5.0)
        assert gaps == [0.0, 0.0]
        assert pad == 1.0

    def test_no_padding_without_a_duration(self):
        gaps, pad = plan_gaps([0.0], [2.0], total_duration=None)
        assert gaps == [0.0]
        assert pad == 0.0

    def test_track_never_ends_early_even_when_speech_overruns(self):
        gaps, pad = plan_gaps([0.0], [7.0], total_duration=5.0)
        assert gaps == [0.0]
        assert pad == 0.0


class TestAtempoFilter:
    def test_speech_that_fits_needs_no_filter(self):
        assert atempo_filter(1.0) is None

    def test_barely_long_speech_is_left_alone(self):
        assert atempo_filter(1.01) is None

    def test_moderate_overrun_is_a_single_stage(self):
        assert atempo_filter(1.5) == "atempo=1.50000"

    def test_large_overrun_is_chained(self):
        assert atempo_filter(3.0) == "atempo=2.00000,atempo=1.50000"
