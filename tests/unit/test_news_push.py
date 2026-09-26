"""Check scheduled news wiring, clock boundaries and isolated retry behavior."""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, FrozenSet, Mapping

import pytest

from kisara.bot import main as bot_main
from kisara.bot.adapters import onebot_v11
from kisara.bot.adapters.onebot_v11 import OneBotError, OneBotV11Adapter
from kisara.bot.contracts import OutgoingMessage
from kisara.config import Settings
from kisara.config.setu import SetuConfig
from kisara.infrastructure.persistence.news_delivery import NewsDeliveryStore


def _settings(
    tmp_path: Path, users: FrozenSet[str] = frozenset({"123"}),
    groups: FrozenSet[str] = frozenset(),
) -> Settings:
    """Keep unrelated features disabled while preserving startup contracts."""
    return Settings(
        "onebot", "test", users, bool(groups), groups,
        onebot_ws_url="ws://napcat:3001", onebot_access_token="test-token",
        chat_enabled=False, tarot_enabled=False,
        news_push_groups=groups, news_push_users=users, state_dir=str(tmp_path),
    )


@pytest.mark.parametrize("enabled", [False, True])
def test_main_wires_private_only_news_factory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, enabled: bool,
) -> None:
    """Personal-only startup injects the dated payload factory; empty targets do not."""
    settings = _settings(tmp_path, frozenset({"123"}) if enabled else frozenset())
    monkeypatch.setattr(Settings, "from_environment", lambda: settings)
    monkeypatch.setattr(SetuConfig, "load", lambda path: SetuConfig.disabled())
    captured = {}

    class News:
        """Return a dated image without external fetching during startup tests."""

        def __init__(self, **kwargs: Any) -> None:
            """Accept the normal startup cache configuration."""

        def get(self) -> Any:
            """Provide the same shape used by the real news factory."""
            return SimpleNamespace(text="2026-09-27", onebot_image=lambda: "base64://news")

    class Adapter:
        """Capture lifecycle calls without connecting a bot."""

        def start(self) -> None:
            """Record successful startup."""
            captured["started"] = True

        def close(self) -> None:
            """Record normal cleanup."""
            captured["closed"] = True

    def create_adapter(settings: Settings, handler: Any, factory: Any, setu: Any) -> Adapter:
        """Capture the factory selected by the real main function."""
        captured["factory"] = factory
        return Adapter()

    monkeypatch.setattr(bot_main, "DailyNews", News)
    monkeypatch.setattr(bot_main, "create_adapter", create_adapter)
    assert bot_main.main() == 0
    assert captured["started"] and captured["closed"]
    if enabled:
        assert captured["factory"]() == OutgoingMessage("2026-09-27", ("base64://news",))
    else:
        assert captured["factory"] is None


def test_private_factory_assembly_uses_existing_state_store(tmp_path: Path) -> None:
    """The real adapter assembly injects durable state for personal-only scheduling."""
    adapter = bot_main.create_adapter(
        _settings(tmp_path), lambda event: None,
        lambda: OutgoingMessage("news", ("base64://news",)),
    )
    assert isinstance(adapter, OneBotV11Adapter)
    assert adapter._delivery_store is not None
    assert not adapter._news_push_groups
    assert adapter._news_push_users == ("123",)
    adapter._delivery_store.mark_private_sent("2026-09-27", "123")
    assert NewsDeliveryStore(str(tmp_path)).was_private_sent("2026-09-27", "123")


@pytest.mark.parametrize("hour, minute, second", [(10, 29, 59), (10, 30, 0), (23, 59, 0)])
def test_private_push_waits_until_shared_due_time_and_catches_up_today(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    hour: int, minute: int, second: int,
) -> None:
    """The due-time boundary uses UTC+8 and never backfills earlier days."""
    store = NewsDeliveryStore(str(tmp_path))
    calls = []
    factory_calls = []
    now = datetime(2026, 9, 27, hour, minute, second, tzinfo=timezone(timedelta(hours=8)))
    clock = [now]
    sleeps = []

    def factory() -> OutgoingMessage:
        """Track content generation after the schedule is due."""
        factory_calls.append(clock[0])
        return OutgoingMessage("2026-09-27", ("base64://news",))

    adapter = OneBotV11Adapter(_settings(tmp_path), lambda event: None,
                              daily_news_factory=factory, delivery_store=store)

    async def request(action: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        """Capture the private API payload without transport."""
        calls.append((action, params))
        return {}

    async def sleep(seconds: float) -> None:
        """Advance the early clock once, then stop after a due iteration."""
        sleeps.append(seconds)
        if seconds == 1:
            assert not calls and not factory_calls
            clock[0] += timedelta(seconds=seconds)
        else:
            adapter.close()

    monkeypatch.setattr(adapter, "_request", request)
    monkeypatch.setattr(onebot_v11, "datetime", SimpleNamespace(now=lambda zone: clock[0]))
    monkeypatch.setattr(onebot_v11, "asyncio", SimpleNamespace(
        sleep=sleep, get_running_loop=asyncio.get_running_loop,
    ))
    asyncio.run(adapter._run_daily_news())
    assert sleeps == ([1, 900] if hour == 10 and minute == 29 else [900])
    assert len(factory_calls) == 1
    assert calls == [("send_private_msg", {
        "user_id": 123, "message": [
            {"type": "text", "data": {"text": "2026-09-27"}},
            {"type": "image", "data": {"file": "base64://news"}},
        ],
    })]
    assert store.was_private_sent("2026-09-27", "123")
    assert not store.was_private_sent("2026-09-26", "123")


def test_mixed_targets_share_content_and_retry_only_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """One failed group and user do not stop others or repeat completed sends."""
    store = NewsDeliveryStore(str(tmp_path))
    store.mark_sent("2026-09-27", "123")
    calls = []
    factory_calls = []
    sleeps = []
    clock = [datetime(2026, 9, 27, 11, tzinfo=timezone(timedelta(hours=8)))]
    failures = {("send_group_msg", 456), ("send_private_msg", 123)}

    def factory() -> OutgoingMessage:
        """Make each iteration's payload identifiable."""
        factory_calls.append(True)
        return OutgoingMessage(f"iteration-{len(factory_calls)}", ("base64://news",))

    adapter = OneBotV11Adapter(
        _settings(tmp_path, frozenset({"123", "789"}), frozenset({"123", "456", "789"})),
        lambda event: None, daily_news_factory=factory, delivery_store=store,
    )

    async def request(action: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        """Fail each selected target once and record every attempted send."""
        identifier = params.get("group_id", params.get("user_id"))
        calls.append((action, identifier, params["message"][0]["data"]["text"]))
        key = (action, identifier)
        if key in failures:
            failures.remove(key)
            raise OneBotError("simulated failure")
        return {}

    async def sleep(seconds: float) -> None:
        """Allow two pending iterations followed by the next-day wait."""
        sleeps.append(seconds)
        if len(sleeps) == 1:
            assert not store.was_sent("2026-09-27", "456")
            assert not store.was_private_sent("2026-09-27", "123")
            assert store.was_private_sent("2026-09-27", "789")
        if len(sleeps) < 3:
            clock[0] += timedelta(seconds=seconds)
        else:
            adapter.close()

    monkeypatch.setattr(adapter, "_request", request)
    monkeypatch.setattr(onebot_v11, "datetime", SimpleNamespace(now=lambda zone: clock[0]))
    monkeypatch.setattr(onebot_v11, "asyncio", SimpleNamespace(
        sleep=sleep, get_running_loop=asyncio.get_running_loop,
    ))
    asyncio.run(adapter._run_daily_news())
    assert len(factory_calls) == 2
    assert calls == [
        ("send_group_msg", 456, "iteration-1"),
        ("send_group_msg", 789, "iteration-1"),
        ("send_private_msg", 123, "iteration-1"),
        ("send_private_msg", 789, "iteration-1"),
        ("send_group_msg", 456, "iteration-2"),
        ("send_private_msg", 123, "iteration-2"),
    ]
    assert sleeps == [900, 900, 82800]
    assert store.was_sent("2026-09-27", "456")
    assert store.was_private_sent("2026-09-27", "123")

    restarted = OneBotV11Adapter(
        _settings(tmp_path, frozenset({"123", "789"}), frozenset({"123", "456", "789"})),
        lambda event: None, daily_news_factory=factory,
        delivery_store=NewsDeliveryStore(str(tmp_path)),
    )

    async def stop_sleep(seconds: float) -> None:
        """A restarted scheduler waits until tomorrow without regenerating content."""
        assert seconds == 82800
        restarted.close()

    monkeypatch.setattr(onebot_v11.asyncio, "sleep", stop_sleep)
    monkeypatch.setattr(restarted, "_request", request)
    asyncio.run(restarted._run_daily_news())
    assert len(factory_calls) == 2
    assert len(calls) == 6


def test_failed_factory_retries_without_recording_recipients(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Provider failure leaves every target pending for the next recheck."""
    store = NewsDeliveryStore(str(tmp_path))
    attempts = []
    calls = []

    def factory() -> OutgoingMessage:
        """Fail before the first send and recover on the next iteration."""
        attempts.append(True)
        if len(attempts) == 1:
            raise RuntimeError("simulated provider failure")
        return OutgoingMessage("news")

    adapter = OneBotV11Adapter(_settings(tmp_path), lambda event: None,
                              daily_news_factory=factory, delivery_store=store)

    async def request(action: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        """Record the recovered delivery."""
        calls.append(action)
        return {}

    async def sleep(seconds: float) -> None:
        """Retry once after the normal interval."""
        assert seconds == 900
        if len(attempts) == 1:
            assert not calls and not store.was_private_sent("2026-09-27", "123")
        else:
            adapter.close()

    monkeypatch.setattr(adapter, "_request", request)
    monkeypatch.setattr(onebot_v11, "datetime", SimpleNamespace(now=lambda zone:
        datetime(2026, 9, 27, 11, tzinfo=zone)))
    monkeypatch.setattr(onebot_v11, "asyncio", SimpleNamespace(
        sleep=sleep, get_running_loop=asyncio.get_running_loop,
    ))
    asyncio.run(adapter._run_daily_news())
    assert len(attempts) == 2
    assert calls == ["send_private_msg"]
    assert store.was_private_sent("2026-09-27", "123")
