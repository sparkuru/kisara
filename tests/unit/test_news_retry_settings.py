"""Scheduled-news retry configuration follows the selected engine namespace."""

import os
from pathlib import Path

import pytest

from kisara.config import ConfigurationError, Settings


def prepare(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, engine: str) -> None:
    """Isolate feature files and synthetic credentials from local deployment."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KISARA_ENGINE", engine)
    monkeypatch.setenv("ONEBOT_ACCESS_TOKEN", "synthetic")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:synthetic")
    for prefix in ("KISARA", "ONEBOT", "TELEGRAM"):
        monkeypatch.delenv(prefix + "_NEWS_PUSH_RETRY_SECONDS", raising=False)


@pytest.mark.parametrize("engine", ["onebot", "telegram"])
def test_news_retry_default_and_selected_environment_precedence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, engine: str,
) -> None:
    """Only the selected alias can replace a generic interval; parsing is pure."""
    prepare(monkeypatch, tmp_path, engine)
    assert Settings.from_environment().news_push_retry_seconds == 60
    other = "TELEGRAM" if engine == "onebot" else "ONEBOT"
    monkeypatch.setenv(other + "_NEWS_PUSH_RETRY_SECONDS", "wrong-engine")
    monkeypatch.setenv("KISARA_NEWS_PUSH_RETRY_SECONDS", "17")
    assert Settings.from_environment().news_push_retry_seconds == 17
    monkeypatch.setenv(engine.upper() + "_NEWS_PUSH_RETRY_SECONDS", "7")
    before = dict(os.environ)
    assert Settings.from_environment().news_push_retry_seconds == 7
    assert dict(os.environ) == before


@pytest.mark.parametrize("engine", ["onebot", "telegram"])
def test_news_retry_toml_masks_invalid_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, engine: str,
) -> None:
    """An explicit feature value is selected before evaluating its fallback."""
    prepare(monkeypatch, tmp_path, engine)
    monkeypatch.setenv("KISARA_NEWS_PUSH_RETRY_SECONDS", "invalid")
    monkeypatch.setenv(engine.upper() + "_NEWS_PUSH_RETRY_SECONDS", "")
    path = tmp_path / "config" / engine / "features" / "news" / "config.toml"
    path.parent.mkdir(parents=True)
    path.write_text("push_retry_seconds = 9\n")
    assert Settings.from_environment().news_push_retry_seconds == 9


@pytest.mark.parametrize("engine", ["onebot", "telegram"])
@pytest.mark.parametrize("value", ["", "0", "-1", "1.5", "true", "invalid"])
def test_news_retry_rejects_invalid_selected_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, engine: str, value: str,
) -> None:
    """An explicit invalid alias never revives the valid generic fallback."""
    prepare(monkeypatch, tmp_path, engine)
    monkeypatch.setenv("KISARA_NEWS_PUSH_RETRY_SECONDS", "60")
    monkeypatch.setenv(engine.upper() + "_NEWS_PUSH_RETRY_SECONDS", value)
    with pytest.raises(ConfigurationError, match="push_retry_seconds"):
        Settings.from_environment()


@pytest.mark.parametrize("value", ["0", "-1", "true", "false", "1.5", '"60"', '""', "[]"])
def test_news_retry_rejects_non_positive_integer_toml(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, value: str,
) -> None:
    """TOML booleans, strings and fractions cannot configure timer seconds."""
    prepare(monkeypatch, tmp_path, "onebot")
    path = tmp_path / "config/onebot/features/news/config.toml"
    path.parent.mkdir(parents=True)
    path.write_text("push_retry_seconds = " + value + "\n")
    with pytest.raises(ConfigurationError, match="push_retry_seconds"):
        Settings.from_environment()


@pytest.mark.parametrize("value", ["", "0", "-1", "1.5", "true", "invalid"])
def test_news_retry_rejects_invalid_generic_runtime_value(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, value: str,
) -> None:
    """A present generic empty or invalid setting cannot fall back to sixty."""
    prepare(monkeypatch, tmp_path, "onebot")
    monkeypatch.setenv("KISARA_NEWS_PUSH_RETRY_SECONDS", value)
    with pytest.raises(ConfigurationError, match="push_retry_seconds"):
        Settings.from_environment()
