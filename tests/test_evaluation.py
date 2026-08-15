from sub_tools.evaluation.transcription import (
    Segment,
    authoritative_metrics,
    evaluate_transcription,
    parse_srt,
)


def test_parse_srt_returns_seconds_and_text():
    track = parse_srt(
        "1\n00:00:00,000 --> 00:00:01,250\nHello world\n\n"
        "2\n00:00:01,250 --> 00:00:02,000\nAgain\n"
    )

    assert track == [
        Segment(0, 0.0, 1.25, "Hello world"),
        Segment(1, 1.25, 2.0, "Again"),
    ]


def test_identical_track_has_clean_diagnostics():
    reference = [
        Segment(0, 0.0, 2.0, "One two three four five"),
        Segment(1, 2.0, 4.0, "Six seven eight nine ten"),
    ]

    result = evaluate_transcription(reference, reference, 4.0)

    assert result["timing"]["median_abs"] == 0.0
    assert result["intrinsic"]["coverage"]["coverage_ratio"] == 1.0
    assert result["gates"] == []


def test_short_pauses_are_reported_without_triggering_long_gap_gate():
    track = [
        Segment(0, 0.0, 1.0, "One two three four"),
        Segment(1, 1.5, 2.0, "Five six seven eight"),
    ]

    result = evaluate_transcription(track, track, 2.0)
    coverage = result["intrinsic"]["coverage"]

    assert coverage["coverage_ratio"] == 0.75
    assert coverage["uncovered_seconds"] == 0.5
    assert coverage["largest_gap_seconds"] == 0.0
    assert result["gates"] == []


def test_overlaps_are_a_hard_gate():
    reference = [
        Segment(0, 0.0, 1.0, "One two three four"),
        Segment(1, 1.0, 2.0, "Five six seven eight"),
    ]
    hypothesis = [
        Segment(0, 0.0, 1.1, "One two three four"),
        Segment(1, 1.0, 2.0, "Five six seven eight"),
    ]

    result = evaluate_transcription(reference, hypothesis, 2.0)

    assert result["intrinsic"]["coverage"]["overlaps"] == 1
    assert result["gates"] == ["1 overlapping segments"]


def test_authoritative_metrics_use_suber_for_nonparallel_srt(tmp_path):
    reference_path = tmp_path / "reference.srt"
    hypothesis_path = tmp_path / "hypothesis.srt"
    reference_path.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nOne two\n\n"
        "2\n00:00:01,000 --> 00:00:02,000\nThree four\n",
        encoding="utf-8",
    )
    hypothesis_path.write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nOne two three four\n",
        encoding="utf-8",
    )

    result = authoritative_metrics(reference_path, hypothesis_path)

    # SubER intentionally catches the segmentation mismatch even though the
    # words are identical; AS-WER/AS-CER isolate the lexical result.
    assert result["suber"] > 0.0
    assert result["as_wer"] == 0.0
    assert result["as_cer"] == 0.0
