from types import SimpleNamespace

from sub_tools.arguments.parser import build_parser
from sub_tools.config import config
from sub_tools.intelligence import openrouter
from sub_tools.intelligence.pipeline import get_provider


def test_cli_accepts_each_provider_and_key():
    parser = build_parser()
    parsed = parser.parse_args(
        [
            "--provider",
            "openrouter",
            "--model",
            "anthropic/claude-sonnet-4",
            "--openrouter-api-key",
            "router-key",
        ]
    )

    assert parsed.provider == "openrouter"
    assert parsed.model == "anthropic/claude-sonnet-4"
    assert parsed.openrouter_api_key == "router-key"


def test_get_provider_uses_explicit_selection(monkeypatch):
    monkeypatch.setattr(config, "model", "claude-sonnet-4")
    monkeypatch.setattr(config, "provider", "openrouter")
    monkeypatch.setattr(config, "_provider_explicit", True)
    assert get_provider().__name__.endswith("openrouter")


def test_openrouter_routes_audio_and_transcription_models(monkeypatch):
    monkeypatch.setattr(config, "model", "anthropic/claude-sonnet-4")
    monkeypatch.setattr(config, "audio_model", None)
    assert openrouter.accepts_audio() is False
    assert (
        openrouter.generation_model(with_audio=True) == openrouter.DEFAULT_AUDIO_MODEL
    )

    monkeypatch.setattr(config, "model", "openai/whisper-large-v3")
    assert openrouter.accepts_audio() is False
    assert openrouter.uses_transcription_api(config.model) is True
    assert openrouter.generation_model(with_audio=True) == config.model

    monkeypatch.setattr(config, "model", "openai/gpt-4o")
    assert openrouter.accepts_audio() is True


def test_openrouter_segments_are_srt():
    result = openrouter._segments_to_srt(
        [SimpleNamespace(start=0.25, end=1.75, text="Hello")]
    )
    assert result == "1\n00:00:00,250 --> 00:00:01,750\nHello\n"
