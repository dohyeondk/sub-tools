from sub_tools.evaluation import authoritative_metrics


def _write_srt(path, cues):
    path.write_text("\n\n".join(cues) + "\n", encoding="utf-8")


def test_authoritative_metrics_delegate_to_subtitle_edit_rate_for_nonparallel_srt(tmp_path):
    reference_path = tmp_path / "reference.srt"
    hypothesis_path = tmp_path / "hypothesis.srt"
    _write_srt(
        reference_path,
        [
            "1\n00:00:00,000 --> 00:00:01,000\nOne two",
            "2\n00:00:01,000 --> 00:00:02,000\nThree four",
        ],
    )
    _write_srt(
        hypothesis_path,
        ["1\n00:00:00,000 --> 00:00:02,000\nOne two three four"],
    )

    result = authoritative_metrics(reference_path, hypothesis_path)

    assert set(result) == {"suber", "as_wer", "as_cer"}
    assert result["suber"] > 0.0  # segmentation differs, despite identical words
    assert result["as_wer"] == 0.0
    assert result["as_cer"] == 0.0


def test_authoritative_metrics_reports_lexical_errors(tmp_path):
    reference_path = tmp_path / "reference.srt"
    hypothesis_path = tmp_path / "hypothesis.srt"
    cue_reference = "1\n00:00:00,000 --> 00:00:02,000\nOne two"
    cue_hypothesis = "1\n00:00:00,000 --> 00:00:02,000\nOne wrong"
    _write_srt(reference_path, [cue_reference])
    _write_srt(hypothesis_path, [cue_hypothesis])

    result = authoritative_metrics(reference_path, hypothesis_path)

    assert result["suber"] > 0.0
    assert result["as_wer"] > 0.0
    assert result["as_cer"] > 0.0
