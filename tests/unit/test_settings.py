"""Tests for engine-aware environment settings."""

from pathlib import Path

import pytest

from kisara.config import ConfigurationError, Settings


def _clear_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove settings that could leak between environment-based tests."""

    names = (
        "KISARA_ENGINE",
        "KISARA_INSTANCE_ID",
        "KISARA_ALLOWED_USERS",
        "KISARA_GROUPS_ENABLED",
        "KISARA_ALLOWED_GROUPS",
        "ONEBOT_WS_URL",
        "ONEBOT_ACCESS_TOKEN",
        "AppID",
        "APP_ID",
        "AppSecret",
        "APP_SECRET",
    )
    for name in names:
        monkeypatch.delenv(name, raising=False)


def test_settings_default_to_onebot_without_official_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The default engine should not require official bot credentials."""

    _clear_settings(monkeypatch)
    monkeypatch.setenv("ONEBOT_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("KISARA_ALLOWED_USERS", "123, 456")

    settings = Settings.from_environment()

    assert settings.engine == "onebot"
    assert settings.allowed_users == frozenset({"123", "456"})
    assert settings.onebot_access_token == "test-token"
    assert settings.app_id is None


def test_settings_accept_project_official_environment_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The existing AppID and AppSecret names should remain supported."""

    _clear_settings(monkeypatch)
    monkeypatch.setenv("KISARA_ENGINE", "official")
    monkeypatch.setenv("AppID", "test-app-id")
    monkeypatch.setenv("AppSecret", "test-app-secret")

    settings = Settings.from_environment()

    assert settings.engine == "official"
    assert settings.app_id == "test-app-id"
    assert settings.app_secret == "test-app-secret"


def test_settings_reject_missing_selected_engine_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only the selected engine's required configuration should be checked."""

    _clear_settings(monkeypatch)
    monkeypatch.setenv("KISARA_ENGINE", "official")

    with pytest.raises(ConfigurationError, match="AppID"):
        Settings.from_environment()


def test_settings_reject_unknown_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unknown engine names must fail before adapter construction."""

    _clear_settings(monkeypatch)
    monkeypatch.setenv("KISARA_ENGINE", "unknown")

    with pytest.raises(ConfigurationError, match="Unknown KISARA_ENGINE"):
        Settings.from_environment()


def test_settings_reject_invalid_group_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Group configuration should not silently accept ambiguous values."""

    _clear_settings(monkeypatch)
    monkeypatch.setenv("ONEBOT_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("KISARA_GROUPS_ENABLED", "maybe")

    with pytest.raises(ConfigurationError, match="KISARA_GROUPS_ENABLED"):
        Settings.from_environment()


def _feature_file(root: Path, name: str, content: str) -> None:
    """Write one independent feature file in a temporary project root."""
    path = root / "config" / "features" / name / "config.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_independent_feature_files_override_legacy_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Each feature file wins over its old environment settings."""
    _clear_settings(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ONEBOT_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("KISARA_ALLOWED_USERS", "123")
    monkeypatch.setenv("KISARA_ALLOWED_GROUPS", "987")
    monkeypatch.setenv("KISARA_GROUPS_ENABLED", "true")
    monkeypatch.setenv("KISARA_CHAT_TRIGGER_RATE", "invalid")
    monkeypatch.setenv("KISARA_TAROT_SPREAD_RATE", "invalid")
    monkeypatch.setenv("KISARA_NEWS_PUSH_TIME", "invalid")
    monkeypatch.setenv("SAUCENAO_API_KEY", "old")
    monkeypatch.setenv("KISARA_MUSIC_API_URL", "old")
    monkeypatch.setenv("TIANAPI_KEY", "old")
    _feature_file(tmp_path, "chat", 'trigger_rate = 42\n[groups."987"]\nsimilarity_rate = 75\n')
    _feature_file(tmp_path, "tarot", 'spread_rate = 8\n[groups."987"]\nspread_rate = 25\n')
    _feature_file(tmp_path, "news", 'push_groups = ["987"]\npush_time = "07:15"\n')
    _feature_file(tmp_path, "source", 'api_key = "new-source"\n')
    _feature_file(tmp_path, "music", 'api_url = "http://music:3000"\n')
    _feature_file(tmp_path, "love", 'api_key = "new-love"\n')

    settings = Settings.from_environment()

    assert settings.chat_trigger_rate == 42
    assert settings.tarot_spread_rate == 8
    assert settings.news_push_groups == frozenset({"987"})
    assert (settings.news_push_hour, settings.news_push_minute) == (7, 15)
    assert settings.saucenao_key == "new-source"
    assert settings.music_api_url == "http://music:3000"
    assert settings.tianapi_key == "new-love"
    assert settings.group_overrides["987"].chat["similarity_rate"] == 75
    assert settings.group_overrides["987"].tarot_spread_rate == 25


def test_feature_file_rejects_unknown_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """A misspelled feature setting fails on startup."""
    _clear_settings(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ONEBOT_ACCESS_TOKEN", "test-token")
    _feature_file(tmp_path, "chat", "triger_rate = 42\n")

    with pytest.raises(ConfigurationError, match="Unknown chat feature keys"):
        Settings.from_environment()
