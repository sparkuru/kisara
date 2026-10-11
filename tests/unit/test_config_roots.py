"""Selected-engine configuration isolation across settings and startup."""

import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import List, Tuple

import pytest

import kisara.bot.main as startup
from kisara.config import ConfigurationError, Settings
from kisara.config.feature_files import engine_config_root, load_feature


def _prepare(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, engine: str) -> None:
    """Provide isolated credentials without connecting to any adapter."""
    for name in os.environ:
        if name.startswith(("KISARA_", "ONEBOT_", "TELEGRAM_", "OFFICIAL_")):
            monkeypatch.delenv(name)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KISARA_ENGINE", engine)
    monkeypatch.setenv("KISARA_ALLOWED_USERS", "123")
    monkeypatch.setenv("ONEBOT_ACCESS_TOKEN", "synthetic")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:synthetic")
    monkeypatch.setenv("OFFICIAL_APP_ID", "synthetic")
    monkeypatch.setenv("OFFICIAL_APP_SECRET", "synthetic")


def _write_feature(root: Path, feature: str, content: str) -> None:
    """Write a private fixture beneath an explicitly selected config root."""
    path = root / "features" / feature / "config.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.mark.parametrize("engine", ["onebot", "telegram", "official"])
def test_engine_feature_files_are_isolated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, engine: str,
) -> None:
    """Other engines and obsolete root files cannot configure this process."""
    _prepare(monkeypatch, tmp_path, engine)
    monkeypatch.setenv("KISARA_MUSIC_API_URL", "https://environment.invalid")
    for candidate in ("onebot", "telegram", "official"):
        root = tmp_path / "config" / candidate
        _write_feature(root, "music", 'api_url = "https://' + candidate + '.invalid"\n')
        _write_feature(root, "ping", "enabled = false\n" if candidate == engine else "enabled = true\n")
        _write_feature(root, "news", "cache_days = 19\n" if candidate == engine else "cache_days = 42\n")
    _write_feature(tmp_path / "config", "music", 'api_url = "https://obsolete.invalid"\n')
    _write_feature(tmp_path / "config", "help", "invalid = true\n")

    settings = Settings.from_environment()

    assert settings.config_root == Path("config") / engine
    assert settings.music_api_url == "https://" + engine + ".invalid"
    assert not settings.ping_enabled and settings.help_enabled
    assert settings.news_cache_days == 19


@pytest.mark.parametrize("engine", ["onebot", "telegram", "official"])
def test_missing_selected_file_uses_environment_without_legacy_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, engine: str,
) -> None:
    """Absent selected TOML still keeps established env/default semantics."""
    _prepare(monkeypatch, tmp_path, engine)
    _write_feature(tmp_path / "config", "ping", "enabled = false\n")
    monkeypatch.setenv("KISARA_MUSIC_API_URL", "https://environment.invalid")
    _write_feature(tmp_path / "config", "music", 'api_url = "https://obsolete.invalid"\n')
    settings = Settings.from_environment()
    assert settings.ping_enabled and settings.music_api_url == "https://environment.invalid"


@pytest.mark.parametrize("engine", ["onebot", "telegram", "official"])
@pytest.mark.parametrize("content", ["enabled = [", "enabld = true\n", 'enabled = "true"\n'])
def test_invalid_selected_file_fails_without_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, engine: str, content: str,
) -> None:
    """Valid obsolete files cannot hide selected-engine startup errors."""
    _prepare(monkeypatch, tmp_path, engine)
    _write_feature(tmp_path / "config", "ping", "enabled = true\n")
    _write_feature(tmp_path / "config" / engine, "ping", content)
    with pytest.raises(ConfigurationError):
        Settings.from_environment()


@pytest.mark.parametrize("engine", ["onebot", "telegram", "official"])
def test_direct_settings_construction_derives_matching_root(engine: str) -> None:
    """Manual startup fixtures cannot inherit another engine's default root."""
    settings = Settings(engine, "test", frozenset(), False, frozenset())
    assert settings.config_root == engine_config_root(engine) == Path("config") / engine


def test_loader_uses_its_explicit_root(tmp_path: Path) -> None:
    """Loading never consults process cwd or an implicit environment override."""
    root = tmp_path / "chosen"
    _write_feature(root, "help", "enabled = false\n")
    assert load_feature("help", root) == {"enabled": False}
    assert load_feature("help", tmp_path / "missing") == {}
    with pytest.raises(ConfigurationError):
        engine_config_root("../other")


@pytest.mark.parametrize("engine", ["onebot", "official"])
def test_default_group_json_is_selected_engine_local(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, engine: str,
) -> None:
    """JSON group policies follow the same root as feature TOML."""
    _prepare(monkeypatch, tmp_path, engine)
    monkeypatch.setenv("KISARA_ALLOWED_GROUPS", "987")
    for candidate in ("onebot", "official"):
        root = tmp_path / "config" / candidate
        root.mkdir(parents=True)
        rate = 7 if candidate == engine else 42
        (root / "groups.json").write_text(json.dumps({"987": {"tarot": {"spread_rate": rate}}}))
    (tmp_path / "config/groups.json").write_text("invalid legacy JSON")
    settings = Settings.from_environment()
    assert settings.group_overrides["987"].tarot_spread_rate == 7
    _write_feature(tmp_path / "config" / engine, "tarot", '[groups."987"]\nspread_rate = 13\n')
    assert Settings.from_environment().group_overrides["987"].tarot_spread_rate == 13


@pytest.mark.parametrize("engine", ["onebot", "official"])
def test_explicit_group_json_path_is_literal_and_required(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, engine: str,
) -> None:
    """Explicit JSON paths remain relative to cwd and do not rebase or fall back."""
    _prepare(monkeypatch, tmp_path, engine)
    monkeypatch.setenv("KISARA_ALLOWED_GROUPS", "987")
    path = tmp_path / "custom.json"
    path.write_text('{"987": {"chat": {"trigger_rate": 21}}}')
    monkeypatch.setenv("KISARA_GROUP_CONFIG_PATH", "custom.json")
    assert Settings.from_environment().group_overrides["987"].chat["trigger_rate"] == 21
    monkeypatch.setenv("KISARA_GROUP_CONFIG_PATH", "absent.json")
    with pytest.raises(ConfigurationError, match="does not exist"):
        Settings.from_environment()


@pytest.mark.parametrize("engine", ["onebot", "official"])
def test_invalid_default_group_json_is_not_masked(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, engine: str,
) -> None:
    """Missing selected group JSON is optional, malformed selected JSON is not."""
    _prepare(monkeypatch, tmp_path, engine)
    legacy_root = tmp_path / "config"
    legacy_root.mkdir()
    (legacy_root / "groups.json").write_text("invalid legacy JSON")
    assert Settings.from_environment().group_overrides == {}
    root = tmp_path / "config" / engine
    root.mkdir(parents=True)
    (root / "groups.json").write_text("invalid JSON")
    with pytest.raises(ConfigurationError, match="Cannot read group config"):
        Settings.from_environment()


def test_telegram_still_skips_group_and_qq_feature_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Root selection does not enable unsupported Telegram feature parsing."""
    _prepare(monkeypatch, tmp_path, "telegram")
    root = tmp_path / "config/telegram"
    _write_feature(root, "chat", "invalid = true\n")
    (root / "groups.json").write_text("invalid JSON")
    settings = Settings.from_environment()
    assert not settings.chat_enabled and not settings.group_overrides


@pytest.mark.parametrize("engine", ["onebot", "telegram", "official"])
@pytest.mark.parametrize("selected", ["missing", "valid", "invalid"])
def test_archive_startup_uses_same_selected_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, engine: str, selected: str,
) -> None:
    """Dedicated archive loaders share ordinary-feature engine isolation."""
    _prepare(monkeypatch, tmp_path, engine)
    monkeypatch.setenv("TELEGRAM_LOCAL_MODE", "true")
    monkeypatch.setenv("TELEGRAM_API_BASE_URL", "http://local.invalid:8081")
    monkeypatch.setenv("KISARA_TAROT_ENABLED", "false")
    monkeypatch.setenv("KISARA_CHAT_ENABLED", "false")
    for root in (tmp_path / "config", tmp_path / "config/onebot", tmp_path / "config/telegram", tmp_path / "config/official"):
        for feature in ("setu", "tgsetu"):
            _write_feature(root, feature, "invalid_key = true\n")
    feature = "setu" if engine == "onebot" else "tgsetu"
    selected_path = tmp_path / "config" / engine / "features" / feature / "config.toml"
    if selected == "missing":
        selected_path.unlink()
    elif selected == "valid":
        selected_path.write_text('enabled = true\nallowed_users = ["123"]\n')
    services: List[Tuple[str, object]] = []
    adapters: List[Tuple[object, object]] = []

    def capture_setu(config: object, state_dir: str) -> object:
        services.append(("setu", config))
        return SimpleNamespace(config=config)

    def capture_tgsetu(config: object, *args: object) -> object:
        services.append(("tgsetu", config))
        return SimpleNamespace(config=config)

    def create(settings: Settings, handler: object, factory: object, setu: object,
               **kwargs: object) -> object:
        adapters.append((setu, kwargs.get("tgsetu")))
        return SimpleNamespace(start=lambda: None, close=lambda: None)

    monkeypatch.setattr(startup, "Setu", capture_setu)
    monkeypatch.setattr(startup, "TgSetu", capture_tgsetu)
    monkeypatch.setattr(startup, "create_adapter", create)
    assert startup.main() == (2 if selected == "invalid" and engine != "official" else 0)
    if selected == "valid" and engine != "official":
        assert services[0][0] == feature
        assert services[0][1].allowed_users == frozenset({"123"})
        assert len(adapters) == 1 and adapters[0][engine == "telegram"] is not None
    else:
        assert not services
