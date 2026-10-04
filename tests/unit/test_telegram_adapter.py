"""Telegram boundary behavior without accounts or network requests."""

import asyncio
import logging
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("telegram")
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter

from kisara.application.services.daily_news import DailyNewsResult
from kisara.application.services.news_push import DeliveryRejected
from kisara.bot.adapters.telegram import TelegramAdapter, normalize_update, quiet_sdk_logging, split_text
from kisara.bot.contracts import Attachment, MessageEvent, MessageSegment, OutgoingMessage
from kisara.bot.dispatcher import Dispatcher
from kisara.config.settings import Settings


def update(text: str = "/ping", chat_id: int = 123, kind: str = "private",
           user: int = 123, message_id: int = 1, **fields: object) -> object:
    """Synthetic SDK data with enough native context to exercise normalization."""
    data = dict(chat=SimpleNamespace(id=chat_id, type=kind), from_user=SimpleNamespace(id=user, is_bot=False),
                text=text, message_id=message_id, sender_chat=None, is_topic_message=False)
    data.update(fields)
    return SimpleNamespace(message=SimpleNamespace(**data))


def settings(**fields: object) -> Settings:
    values = dict(engine="telegram", instance_id="test", allowed_users=frozenset({"123"}),
                  groups_enabled=True, allowed_groups=frozenset({"-456"}), telegram_token="123:test")
    values.update(fields)
    return Settings(**values)


def dispatcher(**fields: object) -> Dispatcher:
    return Dispatcher(frozenset({"123"}), True, frozenset({"-456"}), **fields)


@pytest.mark.parametrize("text,expected", [("/ping@TestBot", "/ping"), ("/music@testbot hello", "/music hello"),
                                           ("/ping@other", None), ("/news_clear@TestBot", "/news-clear"),
                                           ("/news_clear@other", None)])
def test_target_addressing(text: str, expected: object) -> None:
    event = normalize_update(update(text), "x", "TestBot")
    assert (event.text if event else None) == expected


@pytest.mark.parametrize("fields", [dict(sender_chat=object()), dict(is_topic_message=True),
                                     dict(text=None), dict(from_user=None), dict(chat=SimpleNamespace(id=-1, type="channel"))])
def test_unsupported_updates_ignore(fields: dict) -> None:
    assert normalize_update(update(**fields), "x", "bot") is None
    assert normalize_update(SimpleNamespace(message=None, edited_message=update().message), "x", "bot") is None


def test_authorization_and_chat_scoped_dedup() -> None:
    router = dispatcher()
    first = normalize_update(update(), "x", "bot")
    second = normalize_update(update(chat_id=-456, kind="supergroup"), "x", "bot")
    assert router.dispatch(first) == "pong"
    assert router.dispatch(second) == "pong"
    assert router.dispatch(first) is None
    assert router.dispatch(normalize_update(update(user=789, message_id=2), "x", "bot")) is None
    assert router.dispatch(normalize_update(update(chat_id=-999, kind="group", message_id=2), "x", "bot")) is None


def test_telegram_inventory_switches_and_provider_guard() -> None:
    calls = []
    service = SimpleNamespace(music=lambda query: calls.append(query))
    router = dispatcher(public_services=service, feature_switches={"music": False, "news_push": False})
    event = normalize_update(update("/help"), "x", "bot")
    help_text = router.dispatch(event)
    assert "/ping" in help_text and "/music" not in help_text and "/eat" not in help_text
    for number, text in enumerate(("/song hi", "/music hi", "/eat", "/wallpaper", "/source"), 2):
        assert "Try /help" in router.dispatch(normalize_update(update(text, message_id=number), "x", "bot"))
    assert router.dispatch(normalize_update(update("hello", message_id=10), "x", "bot")) is None
    assert calls == []
    start = router.dispatch(normalize_update(update("/start", message_id=11), "x", "bot"))
    assert start == help_text


def test_news_attachment_keeps_warned_bytes(tmp_path: object) -> None:
    result = DailyNewsResult(date(2026, 10, 4), None, b"immutable-png", "Publication delayed")
    service = SimpleNamespace(get=lambda: result)
    router = dispatcher(daily_news=service)
    payload = router.dispatch_payload(normalize_update(update("/news"), "x", "bot"))
    assert payload.attachments[0].content == b"immutable-png"
    assert "Publication delayed" in payload.text and "2026-10-04" in payload.text
    assert payload.image_urls == ()


def test_plain_text_chunk_limits() -> None:
    chunks = split_text("😀" * 3000 + "a" * 3000)
    assert "".join(chunks) == "😀" * 3000 + "a" * 3000
    assert all(len(chunk.encode("utf-16-le")) // 2 <= 4096 for chunk in chunks)


def test_document_reply_uses_source_chat_and_native_quote() -> None:
    async def run() -> None:
        adapter = TelegramAdapter(settings(), lambda event: None)
        send = AsyncMock(return_value=SimpleNamespace(message_id=99))
        adapter._application = SimpleNamespace(bot=SimpleNamespace(send_document=send))
        event = normalize_update(update("/news", chat_id=-456, kind="group", message_id=7), "x", "bot")
        payload = OutgoingMessage("Notice\nSource", attachments=(Attachment("brief.png", b"png"),))
        await adapter.send_reply(event, payload)
        arguments = send.call_args.kwargs
        assert arguments["chat_id"] == -456 and arguments["caption"] == "Notice\nSource"
        assert arguments["filename"] == "brief.png" and arguments["document"].getvalue() == b"png"
        assert arguments["reply_parameters"].message_id == 7 and arguments["parse_mode"] is None
        assert send.await_count == 1
    asyncio.run(run())


@pytest.mark.parametrize("error,permanent", [(Forbidden("secret"), True), (BadRequest("secret"), True),
                                            (RetryAfter(1000), False)])
def test_known_send_rejections(error: Exception, permanent: bool) -> None:
    async def run() -> None:
        adapter = TelegramAdapter(settings(), lambda event: None)
        adapter._send_payload = AsyncMock(side_effect=error)
        with pytest.raises(DeliveryRejected) as caught:
            await adapter._send_news("123", OutgoingMessage("news"))
        assert caught.value.permanent == permanent
        if not permanent:
            assert caught.value.retry_after == 1000
        assert "secret" not in str(caught.value)
    asyncio.run(run())


def test_network_send_keeps_unknown_result() -> None:
    async def run() -> None:
        adapter = TelegramAdapter(settings(), lambda event: None)
        adapter._send_payload = AsyncMock(side_effect=NetworkError("secret"))
        with pytest.raises(NetworkError):
            await adapter._send_news("123", OutgoingMessage("news"))
    asyncio.run(run())


def test_safe_error_logging(caplog: object) -> None:
    async def run() -> None:
        adapter = TelegramAdapter(settings(), lambda event: None)
        adapter._polling_error(NetworkError("https://api.telegram.org/botTOKEN/getUpdates"))
        await adapter._on_error(None, SimpleNamespace(error=ValueError("botTOKEN")))
        quiet_sdk_logging()
        logging.getLogger("httpx").error("botTOKEN")
        logging.getLogger("telegram.ext.Application").error("botTOKEN")
    with caplog.at_level(logging.WARNING):
        asyncio.run(run())
    assert "TOKEN" not in caplog.text
    assert "NetworkError" in caplog.text


def test_native_gate_authorizes_before_sdk_effects() -> None:
    router = dispatcher()
    native = MessageEvent("telegram", "x", "native-1", "group", "-456", "123", (), {})
    assert router.authorize_native(native, "ping")
    assert not router.authorize_native(native, "ping")
    denied = MessageEvent("telegram", "x", "native-2", "group", "-999", "123", (), {})
    assert not router.authorize_native(denied, "ping")
    assert not router.authorize_native(denied, "eat")


@pytest.mark.parametrize("feature,aliases", [("ping", ("/ping",)), ("help", ("/help", "/ahelp", "/start")),
                                            ("news", ("/news", "/brief", "/news-clear", "/news_clear")),
                                            ("music", ("/music hi", "/song hi"))])
def test_each_switch_blocks_all_its_aliases(feature: str, aliases: tuple) -> None:
    calls = []
    def effect(*arguments: object) -> object:
        calls.append(arguments)
        raise AssertionError("disabled provider called")
    router = dispatcher(daily_news=SimpleNamespace(get=effect, clear_cache=effect),
                        public_services=SimpleNamespace(music=effect), feature_switches={feature: False})
    for number, text in enumerate(aliases, 1):
        result = router.dispatch_result(normalize_update(update(text, message_id=number), "x", "bot"))
        assert "unavailable" in result.reply and result.status == "unhandled"
    assert calls == []


def test_news_clear_native_spelling_routes_and_help_matches() -> None:
    calls = []
    router = dispatcher(daily_news=SimpleNamespace(clear_cache=lambda: calls.append(True) or True))
    help_text = router.dispatch(normalize_update(update("/help"), "x", "bot"))
    assert "/news_clear" in help_text and "/news-clear" not in help_text
    result = router.dispatch_result(normalize_update(update("/news_clear@bot", message_id=2), "x", "bot"))
    assert result.status == "handled" and "已清除" in result.reply
    assert calls == [True]
    invalid = router.dispatch_result(normalize_update(update("/news_clear extra", message_id=3), "x", "bot"))
    assert invalid.status == "error" and invalid.reply == "Usage: /news_clear"
    assert calls == [True]


def test_qq_start_alias_stays_legacy_fallback() -> None:
    router = Dispatcher(frozenset({"123"}), False, frozenset())
    event = MessageEvent("onebot", "x", "1", "private", "123", "123", (MessageSegment("text", {"text": "/start"}),), {})
    assert router.dispatch(event) == "Kisara received: /start"
    assert router.router.match("start", "onebot") is None
