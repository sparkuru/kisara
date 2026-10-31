"""Video export configuration is OneBot-owned and secrets stay out of repr."""

from pathlib import Path

import pytest

from kisara.config import ConfigurationError, Settings


def test_defaults_session_precedence_and_repr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KISARA_ENGINE", "onebot")
    monkeypatch.setenv("ONEBOT_ACCESS_TOKEN", "synthetic")
    monkeypatch.setenv("KISARA_BILIBILI_SESSDATA", "generic-synthetic-session")
    monkeypatch.setenv("ONEBOT_BILIBILI_SESSDATA", "selected-synthetic-session")
    settings = Settings.from_environment()
    assert settings.export_video.sessdata == "selected-synthetic-session"
    assert settings.export_video.max_file_bytes == 512 * 1024 ** 2
    assert settings.export_video.timeout_seconds == 600 and settings.export_video.max_urls == 3
    assert "synthetic-session" not in repr(settings) + repr(settings.export_video)
    monkeypatch.setenv("ONEBOT_BILIBILI_SESSDATA", "")
    assert Settings.from_environment().export_video.sessdata == ""


def test_toml_operational_overrides_are_lazy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ONEBOT_ACCESS_TOKEN", "synthetic")
    monkeypatch.setenv("KISARA_ENGINE", "onebot")
    for suffix in ("VIDEO_ENABLED", "MAX_FILE_BYTES", "TIMEOUT_SECONDS", "MAX_URLS"):
        monkeypatch.setenv("ONEBOT_EXPORT_" + suffix, "invalid-lower-priority-value")
    directory = tmp_path / "config/onebot/features/export"
    directory.mkdir(parents=True)
    (directory / "config.toml").write_text('video_enabled=false\nmax_file_bytes="10M"\ntimeout_seconds=45\nmax_urls=1\n')
    options = Settings.from_environment().export_video
    assert not options.video_enabled and options.max_file_bytes == 10 * 1024 ** 2
    assert options.timeout_seconds == 45 and options.max_urls == 1


@pytest.mark.parametrize("field,value", [
    ("max_file_bytes", "false"), ("max_file_bytes", '"0M"'), ("max_file_bytes", '"3G"'),
    ("timeout_seconds", "false"), ("timeout_seconds", "0"), ("timeout_seconds", '"1"'),
    ("timeout_seconds", "1.2"), ("max_urls", "-1"), ("max_urls", "21"),
    ("video_enabled", '"true"'), ("sessdata", '"must-not-be-in-toml"'),
])
def test_invalid_feature_values_fail_startup_without_echoing_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KISARA_ENGINE", "onebot")
    monkeypatch.setenv("ONEBOT_ACCESS_TOKEN", "synthetic")
    directory = tmp_path / "config/onebot/features/export"
    directory.mkdir(parents=True)
    (directory / "config.toml").write_text(field + "=" + value)
    with pytest.raises(ConfigurationError) as error:
        Settings.from_environment()
    assert "must-not-be-in-toml" not in str(error.value)


@pytest.mark.parametrize("engine", ["telegram", "official"])
def test_other_engines_ignore_video_config_and_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, engine: str) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KISARA_ENGINE", engine)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:synthetic")
    monkeypatch.setenv("OFFICIAL_APP_ID", "synthetic")
    monkeypatch.setenv("OFFICIAL_APP_SECRET", "synthetic")
    monkeypatch.setenv("ONEBOT_BILIBILI_SESSDATA", "bad;cookie")
    monkeypatch.setenv("KISARA_BILIBILI_SESSDATA", "bad;generic")
    directory = tmp_path / ("config/" + engine + "/features/export")
    directory.mkdir(parents=True)
    (directory / "config.toml").write_text("not valid toml")
    assert Settings.from_environment().export_video.sessdata == ""


def test_video_native_cannot_be_made_public(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KISARA_ENGINE", "onebot")
    monkeypatch.setenv("ONEBOT_PUBLIC_FEATURE", "export_video")
    with pytest.raises(ConfigurationError, match="PUBLIC_FEATURE"):
        Settings.from_environment()
