"""Pinned PTB lifecycle and payload protocol using an in-memory Bot API peer."""

import asyncio
import json
import logging
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("telegram")
from telegram.error import BadRequest, Conflict, Forbidden, InvalidToken, NetworkError, RetryAfter, TimedOut
from telegram.ext import Application
from telegram.request import BaseRequest

import kisara.bot.adapters.telegram as transport
from kisara.application.services.daily_news import DailyNewsResult
from kisara.application.services.public import RemoteResult
from kisara.bot.contracts import OutgoingMessage
from kisara.bot.dispatcher import Dispatcher
from kisara.config.settings import Settings
from kisara.infrastructure.persistence.telegram_news import TelegramNewsStore


class BotPeer(BaseRequest):
    """Record official Bot API methods without making HTTP requests."""

    def __init__(self, packets: list = None) -> None:
        self.packets = packets or []
        self.calls = []
        self.closed = False

    @property
    def read_timeout(self) -> float:
        return 30.0

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        self.closed = True

    async def do_request(self, url: str, method: str, request_data: object = None, **kwargs: object) -> tuple:
        operation = url.rsplit("/", 1)[-1]
        parameters = request_data.parameters if request_data else {}
        self.calls.append((operation, parameters, request_data))
        if operation == "getMe":
            result = dict(id=321, is_bot=True, first_name="Kisara", username="TestBot")
        elif operation == "getUpdates":
            await asyncio.sleep(0.01)
            result, self.packets = self.packets, []
        elif operation == "deleteWebhook":
            result = True
        else:
            chat_id = int(parameters["chat_id"])
            result = dict(message_id=len(self.calls), date=1780000000,
                          chat=dict(id=chat_id, type="private" if chat_id > 0 else "supergroup"))
        return 200, json.dumps(dict(ok=True, result=result)).encode()


def packet(number: int, text: str, chat: int = 123, user: int = 123) -> dict:
    return dict(update_id=number, message=dict(message_id=1, date=1780000000,
                chat=dict(id=chat, type="private" if chat > 0 else "supergroup"),
                **{"from": dict(id=user, is_bot=False, first_name="Test")}, text=text))


@pytest.mark.parametrize("operation", ["getMe", "deleteWebhook"])
def test_startup_transport_failure_recovers_with_fresh_clients(
        monkeypatch: object, caplog: object, operation: str) -> None:
    """Pinned SDK initialization/bootstrap failures recover in one adapter run."""
    async def run() -> None:
        peers = []

        class FailedPeer(BotPeer):
            async def do_request(self, url: str, method: str, request_data: object = None,
                                 **kwargs: object) -> tuple:
                if url.endswith(operation):
                    raise NetworkError("https://api.telegram.org/botSECRET/" + operation)
                return await super().do_request(url, method, request_data, **kwargs)

        def create_request(**kwargs: object) -> BotPeer:
            if len(peers) % 2 == 0 and peers:
                assert all(peer.closed for peer in peers)
            peer = FailedPeer() if not peers else BotPeer()
            peers.append(peer)
            return peer

        monkeypatch.setattr(transport, "HTTPXRequest", create_request)
        settings = Settings("telegram", "test", frozenset({"123"}), False, frozenset(),
                            telegram_token="123:synthetic")
        worker_entered = []

        class Archive:
            async def run(self, gateway: object) -> None:
                worker_entered.append(gateway)
                await asyncio.Event().wait()

        adapter = transport.TelegramAdapter(settings, lambda event: None, tgsetu=Archive())
        ready = asyncio.Event()
        monkeypatch.setattr(transport, "publish_readiness",
                            lambda engine, value: ready.set() if value else None)
        transport.quiet_sdk_logging()
        task = asyncio.create_task(adapter._run())
        try:
            await asyncio.wait_for(ready.wait(), 3)
            assert len(peers) == 4 and adapter.status == "running"
            assert worker_entered == [adapter]
            webhook = [call for peer in peers for call in peer.calls if call[0] == "deleteWebhook"]
            assert webhook and all(call[1]["drop_pending_updates"] is False for call in webhook)
        finally:
            adapter.close()
            await asyncio.wait_for(task, 3)
        assert all(peer.closed for peer in peers)
        assert adapter._tgsetu_task is None and adapter._notice_task is None

    with caplog.at_level(logging.INFO, logger="kisara.telegram"):
        asyncio.run(run())
    assert caplog.text.count("Telegram polling ready") == 1
    assert "NetworkError" in caplog.text and "SECRET" not in caplog.text


@pytest.mark.parametrize("operation", ["initialize", "getMe", "deleteWebhook"])
@pytest.mark.parametrize("error_type,attempts", [
    (NetworkError, 3), (TimedOut, 3), (BadRequest, 1), (InvalidToken, 1),
    (Conflict, 1), (Forbidden, 1), (RetryAfter, 1),
])
def test_startup_retry_classification_and_exhaustion(
        monkeypatch: object, caplog: object, operation: str, error_type: type, attempts: int) -> None:
    """Only transient transport errors retry, even across SDK subtype overlaps."""
    async def run() -> None:
        peers, delays, readiness = [], [], []
        monkeypatch.setenv("PTB_TIMEDELTA", "true")
        error = RetryAfter(1) if error_type is RetryAfter else error_type("botSECRET rejected")

        class FailedPeer(BotPeer):
            async def initialize(self) -> None:
                if operation == "initialize":
                    raise error

            async def do_request(self, url: str, method: str, request_data: object = None,
                                 **kwargs: object) -> tuple:
                if url.endswith(operation):
                    raise error
                return await super().do_request(url, method, request_data, **kwargs)

        def create_request(**kwargs: object) -> BotPeer:
            if len(peers) % 2 == 0 and peers:
                assert all(peer.closed for peer in peers)
            peer = FailedPeer() if len(peers) % 2 == 0 else BotPeer()
            peers.append(peer)
            return peer

        async def wait_retry(delay: int) -> bool:
            assert all(peer.closed for peer in peers)
            delays.append(delay)
            return False

        monkeypatch.setattr(transport, "HTTPXRequest", create_request)
        monkeypatch.setattr(transport, "publish_readiness", lambda engine, ready: readiness.append(ready))
        settings = Settings("telegram", "test", frozenset({"123"}), False, frozenset(),
                            telegram_token="123:synthetic")
        adapter = transport.TelegramAdapter(settings, lambda event: None)
        monkeypatch.setattr(adapter, "_wait_startup_retry", wait_retry)
        transport.quiet_sdk_logging()
        with pytest.raises(error_type):
            await asyncio.wait_for(adapter._run(), 1)
        assert len(peers) == attempts * 2
        assert delays == ([1, 2] if attempts == 3 else [])
        assert all(peer.closed for peer in peers) and adapter.status == "stopped"
        assert True not in readiness

    with caplog.at_level(logging.INFO, logger="kisara.telegram"):
        asyncio.run(run())
    phase = "polling_bootstrap" if operation == "deleteWebhook" else "initialize"
    assert "phase=" + phase in caplog.text and "category=" + error_type.__name__ in caplog.text
    assert "SECRET" not in caplog.text and "Telegram polling ready" not in caplog.text


@pytest.mark.parametrize("phase", ["initialize", "getMe", "deleteWebhook"])
@pytest.mark.parametrize("action", ["close", "cancel"])
def test_stop_during_startup_or_backoff_prevents_replacement(
        monkeypatch: object, caplog: object, phase: str, action: str) -> None:
    """Stop and cancellation close both clients without starting another poller."""
    async def run() -> None:
        peers, readiness = [], []
        entered = asyncio.Event()
        release = asyncio.Event()

        class StalledPeer(BotPeer):
            async def initialize(self) -> None:
                if phase == "initialize":
                    entered.set()
                    await release.wait()

            async def do_request(self, url: str, method: str, request_data: object = None,
                                 **kwargs: object) -> tuple:
                if url.endswith(phase):
                    entered.set()
                    if action == "cancel":
                        await asyncio.Event().wait()
                    raise NetworkError("botSECRET temporary failure")
                return await super().do_request(url, method, request_data, **kwargs)

        def create_request(**kwargs: object) -> BotPeer:
            peer = StalledPeer() if not peers else BotPeer()
            peers.append(peer)
            return peer

        monkeypatch.setattr(transport, "HTTPXRequest", create_request)
        monkeypatch.setattr(transport, "publish_readiness", lambda engine, ready: readiness.append(ready))
        settings = Settings("telegram", "test", frozenset({"123"}), False, frozenset(),
                            telegram_token="123:synthetic")
        adapter = transport.TelegramAdapter(settings, lambda event: None)
        transport.quiet_sdk_logging()
        task = asyncio.create_task(adapter._run())
        await asyncio.wait_for(entered.wait(), 1)
        if action == "cancel":
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, 1)
        else:
            if phase == "initialize":
                adapter.close()
                await asyncio.sleep(0)
                release.set()
                await asyncio.wait_for(task, 1)
                assert all(call[0] != "deleteWebhook" for peer in peers for call in peer.calls)
            else:
                for _ in range(100):
                    if all(peer.closed for peer in peers):
                        break
                    await asyncio.sleep(0.001)
                assert all(peer.closed for peer in peers)
                adapter.close()
                await asyncio.wait_for(task, 1)
        assert len(peers) == 2 and all(peer.closed for peer in peers)
        assert adapter.status == "stopped" and True not in readiness

    asyncio.run(run())
    assert "SECRET" not in caplog.text and "Telegram polling ready" not in caplog.text


@pytest.mark.parametrize("action", ["close", "cancel"])
def test_startup_backoff_is_interruptible(monkeypatch: object, action: str) -> None:
    async def run() -> None:
        peers, delays = [], []
        waiting = asyncio.Event()

        class FailedPeer(BotPeer):
            async def do_request(self, url: str, method: str, request_data: object = None,
                                 **kwargs: object) -> tuple:
                raise NetworkError("botSECRET temporary failure")

        def create_request(**kwargs: object) -> BotPeer:
            peer = FailedPeer() if not peers else BotPeer()
            peers.append(peer)
            return peer

        monkeypatch.setattr(transport, "HTTPXRequest", create_request)
        settings = Settings("telegram", "test", frozenset({"123"}), False, frozenset(),
                            telegram_token="123:synthetic")
        adapter = transport.TelegramAdapter(settings, lambda event: None)
        original_wait = adapter._wait_startup_retry

        async def wait_retry(delay: int) -> bool:
            delays.append(delay)
            assert all(peer.closed for peer in peers)
            waiting.set()
            return await original_wait(delay)

        monkeypatch.setattr(adapter, "_wait_startup_retry", wait_retry)
        transport.quiet_sdk_logging()
        task = asyncio.create_task(adapter._run())
        await asyncio.wait_for(waiting.wait(), 1)
        if action == "cancel":
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, 0.5)
        else:
            adapter.close()
            await asyncio.wait_for(task, 0.5)
        assert delays == [1] and len(peers) == 2 and adapter.status == "stopped"

    asyncio.run(run())


@pytest.mark.parametrize("operation", ["getMe", "deleteWebhook"])
def test_failed_cleanup_prevents_retry_preserves_original_category(
        monkeypatch: object, caplog: object, operation: str) -> None:
    async def run() -> None:
        peers = []

        class FailedPeer(BotPeer):
            async def do_request(self, url: str, method: str, request_data: object = None,
                                 **kwargs: object) -> tuple:
                if url.endswith(operation):
                    raise NetworkError("botSECRET original failure")
                return await super().do_request(url, method, request_data, **kwargs)

            async def shutdown(self) -> None:
                self.closed = True
                raise RuntimeError("botSECRET cleanup failed")

        def create_request(**kwargs: object) -> BotPeer:
            peer = FailedPeer() if not peers else BotPeer()
            peers.append(peer)
            return peer

        monkeypatch.setattr(transport, "HTTPXRequest", create_request)
        settings = Settings("telegram", "test", frozenset({"123"}), False, frozenset(),
                            telegram_token="123:synthetic")
        adapter = transport.TelegramAdapter(settings, lambda event: None)
        transport.quiet_sdk_logging()
        with pytest.raises(NetworkError):
            await asyncio.wait_for(adapter._run(), 1)
        assert len(peers) == 2 and all(peer.closed for peer in peers)

    asyncio.run(run())
    assert "category=NetworkError" in caplog.text and "cleanup failed" in caplog.text
    assert "SECRET" not in caplog.text


def test_real_sdk_polling_router_documents_and_shutdown(monkeypatch: object, tmp_path: object,
                                                        caplog: object) -> None:
    async def run() -> None:
        request = BotPeer()
        updates = BotPeer([packet(1, "/ping"), packet(2, "/ping@TestBot", -456),
                           packet(3, "/music hi", 124), packet(4, "/news", 125),
                           packet(5, "/ping", 126, 999), packet(6, "/ping@other", 127),
                           packet(7, "/eat", 128), packet(8, "ordinary", 129)])
        monkeypatch.setattr("kisara.bot.adapters.telegram.HTTPXRequest",
                            lambda **kwargs: updates if kwargs.get("read_timeout") == 35 else request)
        news = SimpleNamespace(get=lambda: DailyNewsResult(date(2026, 10, 4), None, b"PNG", "Delayed publication"))
        music = SimpleNamespace(music=lambda query: RemoteResult("Song — artist\nhttps://music.163.com/#/song?id=1", music_id="1"))
        router = Dispatcher(frozenset({"123"}), True, frozenset({"-456"}), daily_news=news, public_services=music)
        settings = Settings("telegram", "test", frozenset({"123"}), True, frozenset({"-456"}),
                            telegram_token="123:synthetic", telegram_message_log_enabled=True)
        adapter = transport.TelegramAdapter(settings, router.dispatch_payload)
        task = asyncio.create_task(adapter._run())
        try:
            for _ in range(300):
                if len([call for call in request.calls if call[0] in {"sendMessage", "sendDocument"}]) >= 5:
                    break
                await asyncio.sleep(0.01)
            sends = [call for call in request.calls if call[0] in {"sendMessage", "sendDocument"}]
            assert len(sends) == 5
            assert sends[0][1]["text"] == "pong" and sends[1][1]["chat_id"] == -456
            assert "Song — artist" in sends[2][1]["text"]
            document = sends[3]
            assert document[0] == "sendDocument" and "Delayed publication" in document[1]["caption"]
            assert "2026-10-04" in document[1]["caption"]
            assert document[2].multipart_data
            assert "Unknown command" not in sends[4][1]["text"] # unsupported registered /eat
            assert "unavailable" in sends[4][1]["text"]
            assert adapter._application.update_queue.maxsize == 128
        finally:
            adapter.close()
            await asyncio.wait_for(task, 3)
        assert adapter.status == "stopped" and request.closed and updates.closed
    with caplog.at_level(logging.INFO, logger="kisara.telegram"):
        asyncio.run(run())
    messages = [record.getMessage() for record in caplog.records]
    assert "Telegram polling ready" in messages
    assert sum(message.startswith("Received") for message in messages) == 6
    assert sum(message.startswith("Sent") for message in messages) == 5
    assert any("document" in message and "caption=" in message for message in messages)
    assert not any("user=999" in message or "chat=126" in message or "chat=127" in message for message in messages)
    assert "123:synthetic" not in caplog.text


def test_public_tguid_real_sdk_addressing_source_id_and_dedup(
        monkeypatch: object, caplog: object) -> None:
    """Public replies use the original chat, sender UID and scoped message ID."""
    async def run() -> None:
        request = BotPeer()
        first = packet(1, "/tguid", chat=777)
        first["message"]["reply_to_message"] = dict(message_id=42, date=1780000000,
            chat=dict(id=777, type="private"), **{"from": dict(id=999, is_bot=False, first_name="Other")}, text="quote")
        updates = BotPeer([first, packet(2, "/tguid@TestBot", -456),
                           packet(3, "/tguid", 777), packet(4, "/tguid", 778),
                           packet(5, "/tguid@other", 780), packet(6, "/ping", 781),
                           packet(7, "/tguid 999", 779), packet(8, "/tguid@TestBot", -457)])
        monkeypatch.setattr(transport, "HTTPXRequest",
                            lambda **kwargs: updates if kwargs.get("read_timeout") == 35 else request)
        router = Dispatcher(frozenset(), True, frozenset(),
                            public_features={"telegram": frozenset({"tguid"})})
        settings = Settings("telegram", "test", frozenset(), True, frozenset(),
                            telegram_token="123:synthetic", telegram_message_log_enabled=True)
        adapter = transport.TelegramAdapter(settings, router.dispatch_payload)
        task = asyncio.create_task(adapter._run())
        try:
            for _ in range(300):
                if sum(call[0] == "sendMessage" for call in request.calls) >= 5:
                    break
                await asyncio.sleep(0.01)
            sends = [call[1] for call in request.calls if call[0] == "sendMessage"]
            assert [(send["chat_id"], send["text"]) for send in sends] == [
                (777, "123"), (-456, "123"), (778, "123"), (779, "Usage: /tguid"), (-457, "123")]
            assert all(send["reply_parameters"]["message_id"] == 1 for send in sends)
        finally:
            adapter.close()
            await asyncio.wait_for(task, 3)
        assert request.closed and updates.closed
    with caplog.at_level(logging.INFO, logger="kisara.telegram"):
        asyncio.run(run())
    assert not any(record.getMessage().startswith(("Received", "Sent", "No reply")) for record in caplog.records)


@pytest.mark.parametrize("retry_seconds", [60, 7])
def test_scheduler_cancel_before_sdk_stop(monkeypatch: object, tmp_path: object,
                                         retry_seconds: int) -> None:
    async def run() -> None:
        events = []
        entered = asyncio.Event()
        class Scheduler:
            def __init__(self, *args: object, **kwargs: object) -> None:
                assert kwargs["retry_seconds"] == retry_seconds
            async def run(self) -> None:
                entered.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    events.append("scheduler_cancel")
        class Updater:
            running = False
            async def start_polling(self, **kwargs: object) -> None:
                assert callable(kwargs["error_callback"]) and kwargs["drop_pending_updates"] is False
                self.running = True
            async def stop(self) -> None:
                events.append("updater_stop")
                self.running = False
        class App:
            updater = Updater()
            running = False
            bot = SimpleNamespace()
            def add_handler(self, *args: object) -> None:
                pass
            def add_error_handler(self, *args: object) -> None:
                pass
            async def initialize(self) -> None:
                pass
            async def start(self) -> None:
                self.running = True
            async def stop(self) -> None:
                events.append("app_stop")
                self.running = False
            async def shutdown(self) -> None:
                events.append("shutdown")
        app = App()
        class Builder:
            def __getattr__(self, name: str) -> object:
                return (lambda: app) if name == "build" else (lambda *args: self)
        monkeypatch.setattr(transport, "Application", SimpleNamespace(builder=Builder))
        monkeypatch.setattr(transport, "TelegramNewsPush", Scheduler)
        settings = Settings("telegram", "test", frozenset({"123"}), False, frozenset(),
                            telegram_token="123:fake", news_push_users=frozenset({"123"}),
                            news_push_retry_seconds=retry_seconds)
        adapter = transport.TelegramAdapter(settings, lambda event: None, lambda: OutgoingMessage("x"), TelegramNewsStore(str(tmp_path)))
        task = asyncio.create_task(adapter._run())
        await asyncio.wait_for(entered.wait(), 1)
        adapter.close()
        await asyncio.wait_for(task, 1)
        assert events == ["scheduler_cancel", "updater_stop", "app_stop", "shutdown"]
    asyncio.run(run())


def test_revoked_token_mid_poll_stops_and_closes_sdk(monkeypatch: object, caplog: object) -> None:
    async def run() -> None:
        request = BotPeer()
        class RevokedPeer(BotPeer):
            async def do_request(self, url: str, method: str, request_data: object = None, **kwargs: object) -> tuple:
                if url.endswith("getUpdates"):
                    return 401, b'{"ok":false,"error_code":401,"description":"botSECRET revoked"}'
                return await super().do_request(url, method, request_data, **kwargs)
        updates = RevokedPeer()
        monkeypatch.setattr(transport, "HTTPXRequest", lambda **kwargs: updates if kwargs.get("read_timeout") == 35 else request)
        settings = Settings("telegram", "test", frozenset({"123"}), False, frozenset(), telegram_token="123:synthetic")
        adapter = transport.TelegramAdapter(settings, lambda event: None)
        transport.quiet_sdk_logging()
        with pytest.raises(RuntimeError):
            await asyncio.wait_for(adapter._run(), 3)
        assert adapter.status == "stopped" and request.closed and updates.closed
    asyncio.run(run())
    assert "SECRET" not in caplog.text


@pytest.mark.parametrize("failure", ["credentials", "request_initialize"])
def test_partial_initialization_closes_request_clients(monkeypatch: object, caplog: object,
                                                      failure: str) -> None:
    async def run() -> None:
        class FailedPeer(BotPeer):
            async def initialize(self) -> None:
                if failure == "request_initialize":
                    raise RuntimeError("botSECRET initialization failed")

            async def do_request(self, url: str, method: str, request_data: object = None,
                                 **kwargs: object) -> tuple:
                if url.endswith("getMe"):
                    return 401, b'{"ok":false,"error_code":401,"description":"botSECRET rejected"}'
                return await super().do_request(url, method, request_data, **kwargs)

        request, updates = FailedPeer(), BotPeer()
        monkeypatch.setattr(transport, "HTTPXRequest",
                            lambda **kwargs: updates if kwargs.get("read_timeout") == 35 else request)
        settings = Settings("telegram", "test", frozenset({"123"}), False, frozenset(),
                            telegram_token="123:synthetic")
        adapter = transport.TelegramAdapter(settings, lambda event: None)
        transport.quiet_sdk_logging()
        with pytest.raises(InvalidToken if failure == "credentials" else RuntimeError):
            await asyncio.wait_for(adapter._run(), 3)
        assert request.closed and updates.closed and adapter.status == "stopped"

    with caplog.at_level(logging.INFO, logger="kisara.telegram"):
        asyncio.run(run())
    assert "SECRET" not in caplog.text
    assert "Telegram polling ready" not in caplog.text


def test_full_queue_shutdown_drains_bounded_work(monkeypatch: object) -> None:
    async def run() -> None:
        request = BotPeer()
        updates = BotPeer([packet(number, "/ping", 1000 + number) for number in range(1, 202)])
        monkeypatch.setattr(transport, "HTTPXRequest", lambda **kwargs: updates if kwargs.get("read_timeout") == 35 else request)
        settings = Settings("telegram", "test", frozenset({"123"}), False, frozenset(), telegram_token="123:synthetic")
        adapter = transport.TelegramAdapter(settings, lambda event: None)
        entered, release = asyncio.Event(), asyncio.Event()
        async def handle(update: object, context: object) -> None:
            entered.set()
            await release.wait()
        adapter._on_update = handle
        task = asyncio.create_task(adapter._run())
        await asyncio.wait_for(entered.wait(), 1)
        for _ in range(100):
            if adapter._application.update_queue.full():
                break
            await asyncio.sleep(0.01)
        assert adapter._application.update_queue.full()
        adapter.close()
        # Finite in-flight work completes; the consumer remains alive while poller stops.
        release.set()
        await asyncio.wait_for(task, 3)
        assert request.closed and updates.closed and adapter.status == "stopped"
    asyncio.run(run())


@pytest.mark.parametrize("error_type", [RuntimeError, NetworkError])
def test_application_start_failure_emits_no_polling_ready(
        monkeypatch: object, caplog: object, error_type: type) -> None:
    """Polling alone is insufficient evidence for a ready application."""
    async def run() -> None:
        request, updates = BotPeer(), BotPeer()
        monkeypatch.setattr(transport, "HTTPXRequest",
                            lambda **kwargs: updates if kwargs.get("read_timeout") == 35 else request)
        start = AsyncMock(side_effect=error_type("botSECRET start failed"))
        monkeypatch.setattr(Application, "start", start)
        settings = Settings("telegram", "test", frozenset({"123"}), False, frozenset(),
                            telegram_token="123:synthetic", telegram_message_log_enabled=True)
        adapter = transport.TelegramAdapter(settings, lambda event: None)
        transport.quiet_sdk_logging()
        with pytest.raises(error_type):
            await asyncio.wait_for(adapter._run(), 3)
        assert start.await_count == 1
        assert adapter.status == "stopped" and request.closed and updates.closed
    with caplog.at_level(logging.INFO, logger="kisara.telegram"):
        asyncio.run(run())
    assert "Telegram polling ready" not in caplog.text and "SECRET" not in caplog.text


@pytest.mark.parametrize("action", ["close", "fatal"])
def test_stop_during_application_start_never_becomes_ready(
        monkeypatch: object, caplog: object, action: str) -> None:
    async def run() -> None:
        request, updates = BotPeer(), BotPeer()
        monkeypatch.setattr(transport, "HTTPXRequest",
                            lambda **kwargs: updates if kwargs.get("read_timeout") == 35 else request)
        readiness = []
        monkeypatch.setattr(transport, "publish_readiness", lambda engine, ready: readiness.append(ready))
        settings = Settings("telegram", "test", frozenset({"123"}), False, frozenset(),
                            telegram_token="123:synthetic")
        archive = SimpleNamespace(run=AsyncMock())
        adapter = transport.TelegramAdapter(settings, lambda event: None, tgsetu=archive)
        original_start = Application.start

        async def start(application: Application) -> None:
            await original_start(application)
            if action == "fatal":
                adapter._polling_error(Conflict("botSECRET duplicate polling"))
            else:
                adapter.close()
                await asyncio.sleep(0)

        monkeypatch.setattr(Application, "start", start)
        transport.quiet_sdk_logging()
        if action == "fatal":
            with pytest.raises(RuntimeError, match="stopped during startup"):
                await asyncio.wait_for(adapter._run(), 1)
        else:
            await asyncio.wait_for(adapter._run(), 1)
        archive.run.assert_not_awaited()
        assert True not in readiness and request.closed and updates.closed
        assert adapter.status == "stopped"

    with caplog.at_level(logging.INFO, logger="kisara.telegram"):
        asyncio.run(run())
    assert "Telegram polling ready" not in caplog.text and "SECRET" not in caplog.text


def test_real_sdk_local_endpoint_getfile_and_media_gate(monkeypatch: object, tmp_path: object) -> None:
    """Native media uses the configured SDK endpoint and local paths without downloads."""
    async def run() -> None:
        cache = tmp_path / "cache"
        cache.mkdir()
        source = cache / "movie.mp4"
        source.write_bytes(b"complete-media")
        class MediaPeer(BotPeer):
            async def do_request(self, url: str, method: str, request_data: object = None,
                                 **kwargs: object) -> tuple:
                assert url.startswith("http://telegram-bot-api:8081/bot123:synthetic/")
                if url.endswith("getFile"):
                    self.calls.append(("getFile", request_data.parameters, request_data))
                    result = dict(file_id="file", file_unique_id="unique", file_size=14,
                                  file_path=str(source))
                    return 200, json.dumps(dict(ok=True, result=result)).encode()
                return await super().do_request(url, method, request_data, **kwargs)
        request = MediaPeer()
        media = packet(2, "unused")
        media["message"].pop("text")
        media["message"].update(message_id=2, caption="😀 Movie #tag", caption_entities=[
            dict(type="hashtag", offset=9, length=4)], video=dict(
                file_id="file", file_unique_id="unique", width=1920, height=1080,
                duration=10, file_size=14, file_name="movie.mp4", mime_type="video/mp4"))
        denied = json.loads(json.dumps(media))
        denied["update_id"] = 3
        denied["message"]["message_id"] = 3
        denied["message"]["from"]["id"] = 999
        addressed = packet(4, "/tgsetu@other on")
        addressed["message"]["message_id"] = 4
        updates = BotPeer([packet(1, "/tgsetu@TestBot on"), media, denied, addressed])
        monkeypatch.setattr(transport, "HTTPXRequest",
                            lambda **kwargs: updates if kwargs.get("read_timeout") == 35 else request)
        accepted = []
        class Archive:
            config = SimpleNamespace(cache_root=cache)
            async def handle(self, event: object, gateway: object) -> bool:
                accepted.append(event)
                if event.segments[0].kind == "video":
                    assert await gateway.media_path(event.segments[0].data) == source
                    await gateway.send_notice(event.conversation_id, "Saved", event.message_id)
                return True
            async def run(self, gateway: object) -> None:
                await asyncio.Event().wait()
        router = Dispatcher(frozenset({"123"}), False, frozenset(), feature_switches={"tgsetu": True})
        settings = Settings("telegram", "test", frozenset({"123"}), False, frozenset(),
                            telegram_token="123:synthetic", telegram_local_mode=True,
                            telegram_api_base_url="http://telegram-bot-api:8081")
        adapter = transport.TelegramAdapter(settings, router.dispatch_payload, tgsetu=Archive(),
                                            native_authorizer=router.authorize_native)
        task = asyncio.create_task(adapter._run())
        try:
            for _ in range(200):
                if any(call[0] == "sendMessage" for call in request.calls):
                    break
                await asyncio.sleep(0.01)
            assert [event.text for event in accepted] == ["/tgsetu on", ""]
            data = accepted[1].segments[0].data
            assert data["title"] == "😀 Movie" and data["tags"] == ("tag",)
            assert [call[1]["file_id"] for call in request.calls if call[0] == "getFile"] == ["file"]
            assert adapter._application.bot.local_mode
        finally:
            adapter.close()
            await asyncio.wait_for(task, 3)
        assert request.closed and updates.closed and adapter._tgsetu_task is None
    asyncio.run(run())


def test_archive_worker_cancelled_and_awaited_before_sdk_shutdown(monkeypatch: object) -> None:
    async def run() -> None:
        request, updates = BotPeer(), BotPeer()
        monkeypatch.setattr(transport, "HTTPXRequest",
                            lambda **kwargs: updates if kwargs.get("read_timeout") == 35 else request)
        entered = asyncio.Event()
        released = []
        class Archive:
            async def run(self, gateway: object) -> None:
                entered.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    await asyncio.sleep(0.01)
                    assert not request.closed and not updates.closed
                    released.append(True)
        settings = Settings("telegram", "test", frozenset({"123"}), False, frozenset(),
                            telegram_token="123:synthetic")
        adapter = transport.TelegramAdapter(settings, lambda event: None, tgsetu=Archive())
        task = asyncio.create_task(adapter._run())
        await asyncio.wait_for(entered.wait(), 1)
        adapter.close()
        await asyncio.wait_for(task, 3)
        assert released == [True] and request.closed and updates.closed
    asyncio.run(run())


def test_archive_notice_stall_does_not_block_serial_media_acceptance(monkeypatch: object) -> None:
    async def run() -> None:
        send_entered, second_accepted = asyncio.Event(), asyncio.Event()
        class StalledPeer(BotPeer):
            async def do_request(self, url: str, method: str, request_data: object = None,
                                 **kwargs: object) -> tuple:
                if url.endswith("sendMessage"):
                    send_entered.set()
                    await asyncio.Event().wait()
                return await super().do_request(url, method, request_data, **kwargs)
        request = StalledPeer()
        messages = [packet(1, "/tgsetu on"), packet(2, "/tgsetu status")]
        messages[1]["message"]["message_id"] = 2
        updates = BotPeer(messages)
        monkeypatch.setattr(transport, "HTTPXRequest",
                            lambda **kwargs: updates if kwargs.get("read_timeout") == 35 else request)
        class Archive:
            async def handle(self, event: object, gateway: object) -> bool:
                assert await gateway.send_notice(event.conversation_id, "status", event.message_id) == ""
                if event.message_id == "2":
                    second_accepted.set()
                return True
            async def run(self, gateway: object) -> None:
                await asyncio.Event().wait()
        router = Dispatcher(frozenset({"123"}), False, frozenset(), feature_switches={"tgsetu": True})
        settings = Settings("telegram", "test", frozenset({"123"}), False, frozenset(),
                            telegram_token="123:synthetic")
        adapter = transport.TelegramAdapter(settings, router.dispatch_payload, tgsetu=Archive(),
                                            native_authorizer=router.authorize_native)
        task = asyncio.create_task(adapter._run())
        try:
            await asyncio.wait_for(send_entered.wait(), 1)
            await asyncio.wait_for(second_accepted.wait(), 1)
        finally:
            adapter.close()
            await asyncio.wait_for(task, 3)
        assert request.closed and updates.closed
        assert adapter._notice_task is None and adapter._notice_pending is None
    asyncio.run(run())


def test_archive_worker_failure_stops_and_closes_sdk_safely(monkeypatch: object, caplog: object) -> None:
    async def run() -> None:
        request, updates = BotPeer(), BotPeer()
        monkeypatch.setattr(transport, "HTTPXRequest",
                            lambda **kwargs: updates if kwargs.get("read_timeout") == 35 else request)
        class Archive:
            async def run(self, gateway: object) -> None:
                raise RuntimeError("https://api.telegram.org/botSECRET/getFile")
        settings = Settings("telegram", "test", frozenset({"123"}), False, frozenset(),
                            telegram_token="123:synthetic")
        adapter = transport.TelegramAdapter(settings, lambda event: None, tgsetu=Archive())
        with pytest.raises(RuntimeError, match="media worker stopped"):
            await asyncio.wait_for(adapter._run(), 3)
        assert request.closed and updates.closed and adapter.status == "stopped"
        assert adapter._notice_task is None and adapter._tgsetu_task is None
    asyncio.run(run())
    assert "SECRET" not in caplog.text
