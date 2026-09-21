"""Tests for engine-aware environment settings."""

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
