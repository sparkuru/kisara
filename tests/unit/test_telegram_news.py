"""Telegram news receipts, recovery and failure transitions."""

import asyncio
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from kisara.application.services.news_push import DeliveryRejected, TelegramNewsPush
from kisara.application.services import news_push
from kisara.bot.contracts import Attachment, OutgoingMessage
from kisara.infrastructure.persistence.telegram_news import TelegramNewsStore


NOW = datetime(2026, 10, 4, 11, tzinfo=timezone(timedelta(hours=8)))
DAY = "2026-10-04"


def push(tmp_path: object, send: object, factory: object = None, now: datetime = NOW) -> tuple:
    store = TelegramNewsStore(str(tmp_path))
    runner = TelegramNewsPush((("private", "123"), ("group", "-456")), 10, 30,
                              factory or (lambda: OutgoingMessage("warned news", attachments=(Attachment("news.png", b"png"),))),
                              send, store, clock=lambda: now, timestamp=lambda: 100)
    return runner, store


def test_confirmed_news_no_replay_after_restart_and_kind_isolation(tmp_path: object) -> None:
    calls = []
    async def send(target: str, content: OutgoingMessage) -> str:
        calls.append((target, content))
        return "99"
    runner, store = push(tmp_path, send)
    asyncio.run(runner.deliver_due())
    assert len(calls) == 2
    assert calls[0][1] is calls[1][1] and calls[0][1].attachments[0].content == b"png"
    assert store.status(DAY, "private", "123") == "confirmed"
    restarted, store = push(tmp_path, send)
    asyncio.run(restarted.deliver_due())
    assert len(calls) == 2
    assert store.claim(DAY, "group", "123", 100)


@pytest.mark.parametrize("failure,status", [(DeliveryRejected(), "retry"),
                                            (DeliveryRejected(permanent=True), "rejected"),
                                            (TimeoutError(), "uncertain")])
def test_known_failure_versus_uncertain(tmp_path: object, failure: Exception, status: str) -> None:
    send = AsyncMock(side_effect=[failure, "88"])
    runner, store = push(tmp_path, send)
    asyncio.run(runner.deliver_due())
    assert store.status(DAY, "private", "123") == status
    assert store.status(DAY, "group", "-456") == "confirmed"
    assert not store.claim(DAY, "private", "123", 159)
    assert store.claim(DAY, "private", "123", 160) == (status == "retry")


def test_server_retry_after(tmp_path: object) -> None:
    send = AsyncMock(side_effect=DeliveryRejected(retry_after=2000))
    runner, store = push(tmp_path, send)
    asyncio.run(runner.deliver_due())
    assert not store.claim(DAY, "private", "123", 2099)
    assert store.claim(DAY, "private", "123", 2100)


def test_generation_failure_once_per_pass_retries_without_send(tmp_path: object) -> None:
    calls = []
    def factory() -> OutgoingMessage:
        calls.append(1)
        raise ValueError("provider secret")
    send = AsyncMock()
    runner, store = push(tmp_path, send, factory)
    asyncio.run(runner.deliver_due())
    assert calls == [1] and send.await_count == 0
    assert store.status(DAY, "private", "123") == "retry"
    assert store.status(DAY, "group", "-456") == "retry"


def test_failed_checkpoint_preserves_claim_and_restart_uncertain(tmp_path: object, monkeypatch: object) -> None:
    send = AsyncMock(return_value="99")
    runner, store = push(tmp_path, send)
    def fail(*arguments: object) -> None:
        raise sqlite3.OperationalError("disk full")
    monkeypatch.setattr(store, "complete", fail)
    asyncio.run(runner.deliver_due())
    assert store.status(DAY, "private", "123") == "claimed"
    asyncio.run(runner.deliver_due())
    assert send.await_count == 2
    restarted = TelegramNewsStore(str(tmp_path))
    assert restarted.status(DAY, "private", "123") == "uncertain"
    assert not restarted.claim(DAY, "private", "123", 10000)


def test_cancel_during_send_recovers_uncertain(tmp_path: object) -> None:
    async def run() -> None:
        entered = asyncio.Event()
        async def send(target: str, content: OutgoingMessage) -> str:
            entered.set()
            await asyncio.Event().wait()
        runner, store = push(tmp_path, send)
        task = asyncio.create_task(runner.deliver_due())
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert store.status(DAY, "private", "123") == "claimed"
        assert TelegramNewsStore(str(tmp_path)).status(DAY, "private", "123") == "uncertain"
    asyncio.run(run())


def test_due_time_today_only_and_retention(tmp_path: object) -> None:
    send = AsyncMock(return_value="99")
    runner, store = push(tmp_path, send, now=NOW.replace(hour=9))
    store.claim("2026-09-01", "private", "123", 0)
    store.claim("2026-10-03", "private", "123", 0)
    asyncio.run(runner.deliver_due())
    assert send.await_count == 0
    runner._clock = lambda: NOW
    asyncio.run(runner.deliver_due())
    assert send.await_count == 2
    assert store.status("2026-09-01", "private", "123") is None
    assert store.status("2026-10-03", "private", "123") == "claimed"


def test_atomic_claim_duplicate(tmp_path: object) -> None:
    store = TelegramNewsStore(str(tmp_path))
    assert store.claim(DAY, "private", "123", 0)
    assert not store.claim(DAY, "private", "123", 100)


def test_midnight_generation_never_sends_previous_day_work(tmp_path: object) -> None:
    dates = [NOW]
    def factory() -> OutgoingMessage:
        dates[0] = NOW + timedelta(days=1)
        return OutgoingMessage("next day's news")
    send = AsyncMock()
    runner, store = push(tmp_path, send, factory)
    runner._clock = lambda: dates[0]
    asyncio.run(runner.deliver_due())
    assert send.await_count == 0
    assert store.status(DAY, "private", "123") == "rejected"
    assert store.status(DAY, "group", "-456") is None


@pytest.mark.parametrize("retry_seconds", [None, 7])
def test_generation_retry_waits_from_failure_and_recovers_once(
    tmp_path: Path, retry_seconds: object,
) -> None:
    """A slow failed generation waits the whole interval before safe recovery."""
    stamp = [100.0]
    attempts = []
    send = AsyncMock(return_value="99")
    store = TelegramNewsStore(str(tmp_path))

    def factory() -> OutgoingMessage:
        """Model ten seconds spent failing before a successful second pass."""
        attempts.append(stamp[0])
        if len(attempts) == 1:
            stamp[0] += 10
            raise TimeoutError("synthetic handshake timeout")
        return OutgoingMessage("recovered news")

    options = {} if retry_seconds is None else {"retry_seconds": retry_seconds}
    runner = TelegramNewsPush(
        (("private", "123"), ("group", "-456")), 10, 30, factory, send, store,
        clock=lambda: NOW, timestamp=lambda: stamp[0], **options,
    )
    asyncio.run(runner.deliver_due())
    deadline = 110 + (60 if retry_seconds is None else retry_seconds)
    stamp[0] = deadline - 1
    asyncio.run(runner.deliver_due())
    assert attempts == [100] and send.await_count == 0
    stamp[0] = deadline
    asyncio.run(runner.deliver_due())
    assert attempts == [100, deadline] and send.await_count == 2
    assert store.status(DAY, "private", "123") == "confirmed"
    assert store.status(DAY, "group", "-456") == "confirmed"
    asyncio.run(runner.deliver_due())
    assert len(attempts) == 2 and send.await_count == 2


@pytest.mark.parametrize("retry_after", [3, 2000])
def test_rejection_retry_respects_failure_completion_and_longer_server_wait(
    tmp_path: Path, retry_after: int,
) -> None:
    """Server and configured delays are both measured after the failed send."""
    stamp = [100.0]
    attempts = []
    store = TelegramNewsStore(str(tmp_path))

    async def send(target: str, content: OutgoingMessage) -> str:
        """Fail once after fifteen seconds, then confirm the retry."""
        attempts.append(stamp[0])
        if len(attempts) == 1:
            stamp[0] += 15
            raise DeliveryRejected(retry_after=retry_after)
        return "99"

    runner = TelegramNewsPush(
        (("private", "123"),), 10, 30, lambda: OutgoingMessage("news"), send, store,
        clock=lambda: NOW, timestamp=lambda: stamp[0], retry_seconds=7,
    )
    asyncio.run(runner.deliver_due())
    deadline = 115 + max(7, retry_after)
    stamp[0] = deadline - 1
    asyncio.run(runner.deliver_due())
    assert attempts == [100]
    stamp[0] = deadline
    asyncio.run(runner.deliver_due())
    assert attempts == [100, deadline]


def test_short_retry_interval_controls_owned_loop_and_cancellation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """A sub-thirty-second retry is not hidden behind the old polling cadence."""
    sleeps = []
    send = AsyncMock(return_value="99")
    store = TelegramNewsStore(str(tmp_path))
    runner = TelegramNewsPush(
        (("private", "123"),), 10, 30, lambda: OutgoingMessage("news"), send, store,
        clock=lambda: NOW, timestamp=lambda: 100, retry_seconds=7,
    )

    async def sleep(seconds: float) -> None:
        """Cancel the owned wait without waiting on a real wall clock."""
        sleeps.append(seconds)
        raise asyncio.CancelledError

    monkeypatch.setattr(news_push, "asyncio", SimpleNamespace(
        sleep=sleep, get_running_loop=asyncio.get_running_loop,
        CancelledError=asyncio.CancelledError,
    ))
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(runner.run())
    assert sleeps == [7]
    assert store.status(DAY, "private", "123") == "confirmed"
