"""Pinned PTB lifecycle and payload protocol using an in-memory Bot API peer."""

import asyncio
import json
import logging
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("telegram")
from telegram.error import InvalidToken
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


def test_scheduler_cancel_before_sdk_stop(monkeypatch: object, tmp_path: object) -> None:
    async def run() -> None:
        events = []
        entered = asyncio.Event()
        class Scheduler:
            def __init__(self, *args: object) -> None:
                pass
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
                            telegram_token="123:fake", news_push_users=frozenset({"123"}))
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


def test_application_start_failure_emits_no_polling_ready(monkeypatch: object, caplog: object) -> None:
    """Polling alone is insufficient evidence for a ready application."""
    async def run() -> None:
        request, updates = BotPeer(), BotPeer()
        monkeypatch.setattr(transport, "HTTPXRequest",
                            lambda **kwargs: updates if kwargs.get("read_timeout") == 35 else request)
        monkeypatch.setattr(Application, "start", AsyncMock(side_effect=RuntimeError("botSECRET start failed")))
        settings = Settings("telegram", "test", frozenset({"123"}), False, frozenset(),
                            telegram_token="123:synthetic", telegram_message_log_enabled=True)
        adapter = transport.TelegramAdapter(settings, lambda event: None)
        transport.quiet_sdk_logging()
        with pytest.raises(RuntimeError):
            await asyncio.wait_for(adapter._run(), 3)
        assert adapter.status == "stopped" and request.closed and updates.closed
    with caplog.at_level(logging.INFO, logger="kisara.telegram"):
        asyncio.run(run())
    assert "Telegram polling ready" not in caplog.text and "SECRET" not in caplog.text
