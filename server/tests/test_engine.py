import pytest

from app.engine import selected_engine


@pytest.mark.parametrize("value", ["gemini", "ollama", "offline"])
def test_selected_engine_explicit(monkeypatch, value):
    monkeypatch.setenv("AI_ENGINE", value)
    assert selected_engine() == value


def test_auto_prefers_gemini(monkeypatch):
    monkeypatch.setenv("AI_ENGINE", "auto")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert selected_engine() == "gemini"
