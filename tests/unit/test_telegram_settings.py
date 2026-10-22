"""Selected Telegram configuration and retained feature precedence."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from kisara.config.settings import ConfigurationError, Settings
from kisara.bot.contracts import MessageEvent, MessageSegment


@pytest.mark.parametrize("public,expected", [(None, "789"), ("", None)])
def test_startup_injects_selected_public_features(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, public: object, expected: object) -> None:
    """Use the real startup's shared handler, including environment-only defaults."""
    import kisara.bot.main as startup
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KISARA_ENGINE", "telegram")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:synthetic")
    monkeypatch.setenv("TELEGRAM_ALLOWED_USERS", "")
    monkeypatch.delenv("KISARA_PUBLIC_FEATURE", raising=False)
    monkeypatch.delenv("TELEGRAM_PUBLIC_FEATURE", raising=False)
    if public is not None:
        monkeypatch.setenv("TELEGRAM_PUBLIC_FEATURE", public)
    results = []
    event = MessageEvent("telegram", "test", "1", "private", "789", "789",
                         (MessageSegment("text", {"text": "/tguid"}),), {})
    def create(settings: Settings, handler: object, *args: object, **kwargs: object) -> object:
        results.append(handler(event))
        return SimpleNamespace(start=lambda: None, close=lambda: None)
    monkeypatch.setattr(startup, "create_adapter", create)
    assert startup.main() == 0
    assert results == [expected]


def prepare(monkeypatch: object, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KISARA_ENGINE", "telegram")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:synthetic")
    monkeypatch.setenv("KISARA_ALLOWED_USERS", "123")


def test_telegram_skips_qq_features_and_credentials(monkeypatch: object, tmp_path: Path) -> None:
    prepare(monkeypatch, tmp_path)
    for name in ("chat", "tarot", "source", "love"):
        directory = tmp_path / "config/telegram/features" / name
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
    directory = tmp_path / "config/telegram/features/news"
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


def test_bot_api_default_and_explicit_local_settings(monkeypatch: object, tmp_path: Path) -> None:
    prepare(monkeypatch, tmp_path)
    monkeypatch.delenv("TELEGRAM_API_BASE_URL", raising=False)
    monkeypatch.delenv("TELEGRAM_LOCAL_MODE", raising=False)
    configured = Settings.from_environment()
    assert configured.telegram_api_base_url == "https://api.telegram.org"
    assert not configured.telegram_local_mode
    monkeypatch.setenv("TELEGRAM_API_BASE_URL", "http://telegram-bot-api:8081/")
    monkeypatch.setenv("TELEGRAM_LOCAL_MODE", "true")
    configured = Settings.from_environment()
    assert configured.telegram_api_base_url == "http://telegram-bot-api:8081"
    assert configured.telegram_local_mode


@pytest.mark.parametrize("name,value", [
    ("TELEGRAM_API_BASE_URL", "ftp://server"), ("TELEGRAM_API_BASE_URL", ""),
    ("TELEGRAM_API_BASE_URL", "http://user:secret@server:8081"),
    ("TELEGRAM_API_BASE_URL", "http://server:8081/?token=SECRET"),
    ("TELEGRAM_API_BASE_URL", "http://server:8081/#fragment"),
    ("TELEGRAM_API_BASE_URL", "http://server:invalid"),
    ("TELEGRAM_API_BASE_URL", "http://some host:8081"),
    ("TELEGRAM_LOCAL_MODE", "sometimes"), ("TELEGRAM_LOCAL_MODE", "true"),
])
def test_invalid_bot_api_settings_rejected(monkeypatch: object, tmp_path: Path,
                                          name: str, value: str) -> None:
    prepare(monkeypatch, tmp_path)
    monkeypatch.delenv("TELEGRAM_API_BASE_URL", raising=False)
    monkeypatch.delenv("TELEGRAM_LOCAL_MODE", raising=False)
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigurationError) as caught:
        Settings.from_environment()
    assert "SECRET" not in str(caught.value)


@pytest.mark.parametrize("engine", ["onebot", "official"])
def test_unselected_bot_api_settings_ignored(monkeypatch: object, tmp_path: Path, engine: str) -> None:
    prepare(monkeypatch, tmp_path)
    monkeypatch.setenv("KISARA_ENGINE", engine)
    monkeypatch.setenv("ONEBOT_ACCESS_TOKEN", "synthetic-onebot")
    monkeypatch.setenv("OFFICIAL_APP_ID", "synthetic-app")
    monkeypatch.setenv("OFFICIAL_APP_SECRET", "synthetic-secret")
    monkeypatch.setenv("TELEGRAM_API_BASE_URL", "invalid")
    monkeypatch.setenv("TELEGRAM_LOCAL_MODE", "invalid")
    configured = Settings.from_environment()
    assert not configured.telegram_local_mode
    assert configured.telegram_api_base_url == "https://api.telegram.org"


@pytest.mark.parametrize("case", ["no_local", "disallowed", "valid"])
def test_archive_startup_validation_and_native_injection(monkeypatch: object, tmp_path: Path,
                                                        case: str) -> None:
    import kisara.bot.main as startup
    from types import SimpleNamespace
    prepare(monkeypatch, tmp_path)
    config = tmp_path / "config/telegram/features/tgsetu/config.toml"
    config.parent.mkdir(parents=True)
    user = "999" if case == "disallowed" else "123"
    config.write_text('enabled = true\nallowed_users = ["' + user + '"]\n')
    if case != "no_local":
        monkeypatch.setenv("TELEGRAM_LOCAL_MODE", "true")
        monkeypatch.setenv("TELEGRAM_API_BASE_URL", "http://telegram-bot-api:8081")
    captured = []
    service = SimpleNamespace()
    monkeypatch.setattr(startup, "TgSetu", lambda *args: service)
    def create(*args: object, **kwargs: object) -> object:
        captured.append((args, kwargs))
        return SimpleNamespace(start=lambda: None, close=lambda: None)
    monkeypatch.setattr(startup, "create_adapter", create)
    assert startup.main() == (0 if case == "valid" else 2)
    if case != "valid":
        assert captured == []
    else:
        args, injected = captured[0]
        assert args[3] is None and injected["tgsetu"] is service
        router = injected["native_authorizer"].__self__
        assert router.router.eligible("tgsetu", "telegram")
        assert "/tgsetu" in router.router.help("telegram")


def test_explicitly_disabled_archive_config_stays_out_of_effective_registry(
        monkeypatch: object, tmp_path: Path) -> None:
    """A present false TOML keeps startup and Telegram help inert."""
    import kisara.bot.main as startup
    from types import SimpleNamespace

    prepare(monkeypatch, tmp_path)
    config = tmp_path / "config/telegram/features/tgsetu/config.toml"
    config.parent.mkdir(parents=True)
    config.write_text('enabled = false\nallowed_users = ["123"]\n')
    constructed = []
    captured = []
    monkeypatch.setattr(startup, "TgSetu", lambda *args: constructed.append(args))

    def create(*args: object, **kwargs: object) -> object:
        captured.append((args, kwargs))
        return SimpleNamespace(start=lambda: None, close=lambda: None)

    monkeypatch.setattr(startup, "create_adapter", create)
    assert startup.main() == 0
    assert constructed == [] and captured[0][1] == {}
    router = captured[0][0][1].__self__
    assert not router.router.eligible("tgsetu", "telegram")
    assert "/tgsetu" not in router.router.help("telegram")
