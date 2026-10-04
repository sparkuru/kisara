"""Selected Telegram configuration and retained feature precedence."""

from pathlib import Path

import pytest

from kisara.config.settings import ConfigurationError, Settings


def prepare(monkeypatch: object, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KISARA_ENGINE", "telegram")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:synthetic")
    monkeypatch.setenv("KISARA_ALLOWED_USERS", "123")


def test_telegram_skips_qq_features_and_credentials(monkeypatch: object, tmp_path: Path) -> None:
    prepare(monkeypatch, tmp_path)
    for name in ("chat", "tarot", "source", "love"):
        directory = tmp_path / "config/features" / name
        directory.mkdir(parents=True)
        (directory / "config.toml").write_text("invalid_key = true")
    monkeypatch.setenv("KISARA_CHAT_TRIGGER_RATE", "invalid")
    monkeypatch.setenv("ONEBOT_WS_URL", "not-a-url")
    settings = Settings.from_environment()
    assert settings.telegram_token == "123:synthetic" and settings.onebot_access_token is None
    assert not settings.chat_enabled and not settings.tarot_enabled
    assert settings.news_enabled and settings.news_push_enabled


def test_independent_switches_toml_override_env(monkeypatch: object, tmp_path: Path) -> None:
    prepare(monkeypatch, tmp_path)
    monkeypatch.setenv("KISARA_NEWS_ENABLED", "true")
    monkeypatch.setenv("KISARA_NEWS_PUSH_ENABLED", "false")
    directory = tmp_path / "config/features/news"
    directory.mkdir(parents=True)
    (directory / "config.toml").write_text('enabled = false\npush_enabled = true\npush_users = ["123"]')
    settings = Settings.from_environment()
    assert not settings.news_enabled and settings.news_push_enabled
    assert settings.news_push_users == frozenset({"123"})


@pytest.mark.parametrize("name,value", [("KISARA_ALLOWED_USERS", "0123"), ("KISARA_ALLOWED_USERS", "-123"),
                                       ("KISARA_ALLOWED_GROUPS", "123"), ("KISARA_ALLOWED_GROUPS", "-0123"),
                                       ("KISARA_NEWS_PUSH_USERS", "999")])
def test_invalid_ids_and_disallowed_targets(monkeypatch: object, tmp_path: Path, name: str, value: str) -> None:
    prepare(monkeypatch, tmp_path)
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigurationError):
        Settings.from_environment()


def test_group_and_private_subscriptions(monkeypatch: object, tmp_path: Path) -> None:
    prepare(monkeypatch, tmp_path)
    monkeypatch.setenv("KISARA_GROUPS_ENABLED", "true")
    monkeypatch.setenv("KISARA_ALLOWED_GROUPS", "-100123")
    monkeypatch.setenv("KISARA_NEWS_PUSH_GROUPS", "-100123")
    monkeypatch.setenv("KISARA_NEWS_PUSH_USERS", "123")
    settings = Settings.from_environment()
    assert settings.news_push_groups == frozenset({"-100123"})
    assert settings.news_push_users == frozenset({"123"})


@pytest.mark.parametrize("manual,push_enabled,targets,has_factory", [(False, True, "123", True),
                                                                  (True, False, "123", False),
                                                                  (False, False, "", False),
                                                                  (True, True, "", False)])
def test_startup_consumes_independent_manual_push_flags(monkeypatch: object, tmp_path: Path,
                                                      manual: bool, push_enabled: bool, targets: str,
                                                      has_factory: bool) -> None:
    import kisara.bot.main as startup
    from datetime import date
    from types import SimpleNamespace
    from kisara.application.services.daily_news import DailyNewsResult
    prepare(monkeypatch, tmp_path)
    monkeypatch.setenv("KISARA_NEWS_ENABLED", str(manual))
    monkeypatch.setenv("KISARA_NEWS_PUSH_ENABLED", str(push_enabled))
    monkeypatch.setenv("KISARA_NEWS_PUSH_USERS", targets)
    captured = []
    monkeypatch.setattr(startup, "DailyNews", lambda **kwargs: SimpleNamespace(
        get=lambda: DailyNewsResult(date(2026, 10, 4), None, b"PNG")))
    class Adapter:
        def start(self) -> None:
            pass
        def close(self) -> None:
            pass
    def create(settings: Settings, handler: object, factory: object, setu: object) -> Adapter:
        assert setu is None and not settings.chat_enabled and not settings.tarot_enabled
        captured.append(factory)
        if factory is not None:
            assert factory().attachments[0].content == b"PNG"
        return Adapter()
    monkeypatch.setattr(startup, "create_adapter", create)
    assert startup.main() == 0
    assert (captured[0] is not None) == has_factory


def test_telegram_outer_startup_error_is_sanitized(monkeypatch: object, tmp_path: Path, caplog: object) -> None:
    import kisara.bot.main as startup
    prepare(monkeypatch, tmp_path)
    class Adapter:
        def start(self) -> None:
            raise RuntimeError("https://api.telegram.org/botSECRET/getMe")
        def close(self) -> None:
            pass
    monkeypatch.setattr(startup, "create_adapter", lambda *args: Adapter())
    assert startup.main() == 1
    assert "SECRET" not in caplog.text and "Telegram stopped unexpectedly" in caplog.text



def test_telegram_namespaced_subscriptions_and_validation(monkeypatch: object, tmp_path: Path) -> None:
    """Direct Telegram inputs override generic runtime recipients and access."""
    prepare(monkeypatch, tmp_path)
    monkeypatch.setenv("TELEGRAM_ALLOWED_USERS", "456")
    monkeypatch.setenv("TELEGRAM_GROUPS_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_ALLOWED_GROUPS", "-100456")
    monkeypatch.setenv("TELEGRAM_NEWS_PUSH_USERS", "456")
    monkeypatch.setenv("TELEGRAM_NEWS_PUSH_GROUPS", "-100456")
    monkeypatch.setenv("TELEGRAM_NEWS_PUSH_TIME", "09:15")
    monkeypatch.setenv("ONEBOT_ALLOWED_USERS", "999")
    settings = Settings.from_environment()
    assert settings.allowed_users == settings.news_push_users == frozenset({"456"})
    assert settings.allowed_groups == settings.news_push_groups == frozenset({"-100456"})
    assert (settings.news_push_hour, settings.news_push_minute) == (9, 15)
    monkeypatch.setenv("TELEGRAM_NEWS_PUSH_USERS", "999")
    with pytest.raises(ConfigurationError, match="ALLOWED_USERS"):
        Settings.from_environment()


@pytest.mark.parametrize("value,expected", [(None, False), ("", False), ("false", False), ("true", True)])
def test_telegram_message_log_explicit_switch(monkeypatch: object, tmp_path: Path,
                                             value: object, expected: bool) -> None:
    """Message summaries are off by default and enabled only by explicit opt-in."""
    prepare(monkeypatch, tmp_path)
    monkeypatch.delenv("TELEGRAM_MESSAGE_LOG_ENABLED", raising=False)
    if value is not None:
        monkeypatch.setenv("TELEGRAM_MESSAGE_LOG_ENABLED", value)
    assert Settings.from_environment().telegram_message_log_enabled is expected


def test_telegram_message_log_invalid_switch_rejected(monkeypatch: object, tmp_path: Path) -> None:
    prepare(monkeypatch, tmp_path)
    monkeypatch.setenv("TELEGRAM_MESSAGE_LOG_ENABLED", "sometimes")
    with pytest.raises(ConfigurationError, match="TELEGRAM_MESSAGE_LOG_ENABLED"):
        Settings.from_environment()


@pytest.mark.parametrize("engine", ["onebot", "official"])
def test_telegram_logging_switch_ignored_by_other_engines(monkeypatch: object, tmp_path: Path,
                                                        engine: str) -> None:
    """Unselected Telegram configuration cannot break or enable QQ message logging."""
    prepare(monkeypatch, tmp_path)
    monkeypatch.setenv("KISARA_ENGINE", engine)
    monkeypatch.setenv("ONEBOT_ACCESS_TOKEN", "synthetic-onebot")
    monkeypatch.setenv("OFFICIAL_APP_ID", "synthetic-app")
    monkeypatch.setenv("OFFICIAL_APP_SECRET", "synthetic-secret")
    monkeypatch.setenv("TELEGRAM_MESSAGE_LOG_ENABLED", "invalid-for-telegram")
    assert not Settings.from_environment().telegram_message_log_enabled
