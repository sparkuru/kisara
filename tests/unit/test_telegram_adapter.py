"""Telegram boundary behavior without accounts or network requests."""

import asyncio
import logging
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("telegram")
from telegram import MessageEntity
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter

from kisara.application.services.daily_news import DailyNewsResult
from kisara.application.services.news_push import DeliveryRejected
from kisara.bot.adapters.telegram import TelegramAdapter, normalize_update, quiet_sdk_logging, split_text
from kisara.bot.contracts import Attachment, MessageEvent, MessageSegment, OutgoingMessage
from kisara.bot.dispatcher import Dispatcher
from kisara.config.settings import Settings
from kisara.config.tgsetu import TgSetuConfig
from kisara.infrastructure.persistence.tgsetu_files import TgSetuFileSaver


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


def test_opt_in_receive_no_reply_and_content_sanitization(caplog: object) -> None:
    """Allowed input is bounded and escaped after full credential redaction."""
    handled = []
    text = "Hello\n\r\t\x1b[31m\u202e\u2028\u2029 123:test https://api.telegram.org/bot999:OTHERSECRET/getMe " + "x" * 200
    adapter = TelegramAdapter(settings(telegram_message_log_enabled=True),
                              lambda event: handled.append(event.text))
    with caplog.at_level(logging.INFO, logger="kisara.telegram"):
        asyncio.run(adapter._on_update(update(text), SimpleNamespace(bot=SimpleNamespace(username="TestBot"))))
    received = [record.getMessage() for record in caplog.records if record.getMessage().startswith("Received")]
    assert len(received) == 1 and "private message user=123 chat=123" in received[0]
    preview = received[0].split(": ", 1)[1]
    assert len(preview) <= 120 and preview.endswith("…")
    assert all(escaped in preview for escaped in ("\\n", "\\u001b", "\\u202e", "\\u2028", "\\u2029"))
    assert not any(character in preview for character in "\n\r\t\x1b\u202e\u2028\u2029")
    assert "123:test" not in caplog.text and "OTHERSECRET" not in caplog.text
    assert "[redacted]" in preview and "No reply" in caplog.text
    assert handled == [text]


@pytest.mark.parametrize("prefix,secret,fragment", [
    ("a" * 115, "123:test", "123:"),
    ("a" * 85, "https://api.telegram.org/bot999:OTHERSECRET/getMe", "999:"),
])
def test_receive_preview_boundary_redacts_before_truncation(
    caplog: object, prefix: str, secret: str, fragment: str,
) -> None:
    """A preview ending inside a credential must never disclose its prefix."""
    adapter = TelegramAdapter(settings(telegram_message_log_enabled=True), lambda event: None)
    with caplog.at_level(logging.INFO, logger="kisara.telegram"):
        asyncio.run(adapter._on_update(update(prefix + secret + " suffix"),
                                      SimpleNamespace(bot=SimpleNamespace(username="TestBot"))))
    received = [record.getMessage() for record in caplog.records if record.getMessage().startswith("Received")]
    assert len(received) == 1
    preview = received[0].split(": ", 1)[1]
    assert len(preview) <= 120 and "[red" in preview
    assert fragment not in preview and secret not in preview


@pytest.mark.parametrize("enabled,fields", [
    (False, {}), (True, {"user": 789}),
    (True, {"chat_id": -999, "kind": "group"}),
    (True, {"kind": "channel"}), (True, {"is_topic_message": True}),
    (True, {"sender_chat": object()}), (True, {"text": "/ping@other"}),
])
def test_disabled_denied_unsupported_input_logs_no_identity(
    caplog: object, enabled: bool, fields: dict,
) -> None:
    """Logging gates do not change which normalized events reach the handler."""
    handled = []
    adapter = TelegramAdapter(settings(telegram_message_log_enabled=enabled),
                              lambda event: handled.append(event))
    incoming = update(**dict({"text": "secret-body"}, **fields))
    normalized = normalize_update(incoming, adapter.instance_id, "TestBot")
    with caplog.at_level(logging.INFO, logger="kisara.telegram"):
        asyncio.run(adapter._on_update(incoming, SimpleNamespace(bot=SimpleNamespace(username="TestBot"))))
    assert not caplog.records
    assert bool(handled) == (normalized is not None)


def test_allowed_group_receive_and_confirmed_chunk_sends(caplog: object) -> None:
    """Each completed text chunk is logged; group authorization stays in routing."""
    async def run() -> None:
        send = AsyncMock(return_value=SimpleNamespace(message_id=77))
        adapter = TelegramAdapter(settings(telegram_message_log_enabled=True), lambda event: "a" * 5000)
        adapter._application = SimpleNamespace(bot=SimpleNamespace(send_message=send))
        await adapter._on_update(update(chat_id=-456, kind="supergroup"),
                                 SimpleNamespace(bot=SimpleNamespace(username="TestBot")))
        assert send.await_count == 2
    with caplog.at_level(logging.INFO, logger="kisara.telegram"):
        asyncio.run(run())
    messages = [record.getMessage() for record in caplog.records]
    assert "Received group message user=123 chat=-456: /ping" in messages
    sends = [message for message in messages if message.startswith("Sent group text")]
    assert len(sends) == 2 and all("message=77" in message for message in sends)
    assert all(len(message.split(": ", 1)[1]) <= 120 for message in sends)


def test_scheduled_document_logs_metadata_without_bytes_or_token(caplog: object) -> None:
    """Scheduled sends share captioned document success logging after confirmation."""
    async def run() -> None:
        send = AsyncMock(return_value=SimpleNamespace(message_id=88))
        adapter = TelegramAdapter(settings(telegram_message_log_enabled=True), lambda event: None)
        adapter._application = SimpleNamespace(bot=SimpleNamespace(send_document=send))
        payload = OutgoingMessage("News\n123:test", attachments=(
            Attachment("brief\n123:test.png", b"private-media-bytes", "image/png\x1b"),
        ))
        assert await adapter._send_news("123", payload) == "88"
        assert send.await_count == 1
    with caplog.at_level(logging.INFO, logger="kisara.telegram"):
        asyncio.run(run())
    messages = [record.getMessage() for record in caplog.records]
    assert len(messages) == 1 and messages[0].startswith("Sent private document chat=123 message=88")
    assert "bytes=19" in messages[0] and "caption=News\\n[redacted]" in messages[0]
    assert "123:test" not in caplog.text and "private-media-bytes" not in caplog.text
    assert "\x1b" not in messages[0] and "\n" not in messages[0]


@pytest.mark.parametrize("document", [False, True])
def test_failed_sends_do_not_emit_success_summaries(caplog: object, document: bool) -> None:
    """An SDK failure never creates a misleading send-success record."""
    async def run() -> None:
        send = AsyncMock(side_effect=NetworkError("https://api.telegram.org/bot123:test/sendMessage"))
        adapter = TelegramAdapter(settings(telegram_message_log_enabled=True), lambda event: None)
        adapter._application = SimpleNamespace(bot=SimpleNamespace(send_message=send, send_document=send))
        payload = OutgoingMessage("secret-body", attachments=(Attachment("brief.png", b"png"),)) if document else "secret-body"
        event = normalize_update(update(), "test", "TestBot")
        with pytest.raises(NetworkError):
            await adapter.send_reply(event, payload)
    with caplog.at_level(logging.INFO, logger="kisara.telegram"):
        asyncio.run(run())
    assert not caplog.records


@pytest.mark.parametrize("enabled,target", [(False, "123"), (True, "999"), (True, "-999")])
def test_disabled_or_denied_sends_do_not_disclose_content(caplog: object, enabled: bool, target: str) -> None:
    """The log allowlist gates disclosure while leaving existing send calls unchanged."""
    async def run() -> None:
        send = AsyncMock(return_value=SimpleNamespace(message_id=90))
        adapter = TelegramAdapter(settings(telegram_message_log_enabled=enabled), lambda event: None)
        adapter._application = SimpleNamespace(bot=SimpleNamespace(send_message=send))
        assert await adapter._send_news(target, OutgoingMessage("secret-body")) == "90"
        assert send.await_count == 1
    with caplog.at_level(logging.INFO, logger="kisara.telegram"):
        asyncio.run(run())
    assert not caplog.records


@pytest.mark.parametrize("secret", ["123:test", "https://api.telegram.org/bot999:OTHERSECRET/getMe"])
def test_text_chunk_boundary_never_logs_credential_fragments(caplog: object, secret: str) -> None:
    """Chunking cannot bypass redaction by separating token characters."""
    async def run() -> None:
        send = AsyncMock(return_value=SimpleNamespace(message_id=91))
        adapter = TelegramAdapter(settings(telegram_message_log_enabled=True), lambda event: None)
        adapter._application = SimpleNamespace(bot=SimpleNamespace(send_message=send))
        event = normalize_update(update(), "test", "TestBot")
        prefix = "a" * (4096 - len(secret) + 2)
        await adapter.send_reply(event, prefix + secret + " suffix")
        assert send.await_count == 2
        assert "".join(call.kwargs["text"] for call in send.call_args_list) == prefix + secret + " suffix"
    with caplog.at_level(logging.INFO, logger="kisara.telegram"):
        asyncio.run(run())
    messages = [record.getMessage() for record in caplog.records]
    assert len(messages) == 2
    assert "part=1/2" in messages[0] and "part=2/2" in messages[1]
    assert all(message.split(": ", 1)[1] == "a" * 119 + "…" for message in messages)
    assert "123:test" not in caplog.text and "OTHERSECRET" not in caplog.text


def test_partial_chunk_failure_logs_only_confirmed_parts(caplog: object) -> None:
    """A later failed chunk does not invalidate or invent earlier send receipts."""
    async def run() -> None:
        send = AsyncMock(side_effect=[SimpleNamespace(message_id=92), NetworkError("bot123:test failed")])
        adapter = TelegramAdapter(settings(telegram_message_log_enabled=True), lambda event: None)
        adapter._application = SimpleNamespace(bot=SimpleNamespace(send_message=send))
        event = normalize_update(update(), "test", "TestBot")
        with pytest.raises(NetworkError):
            await adapter.send_reply(event, "a" * 5000)
    with caplog.at_level(logging.INFO, logger="kisara.telegram"):
        asyncio.run(run())
    messages = [record.getMessage() for record in caplog.records]
    assert len(messages) == 1 and "part=1/2" in messages[0]
    assert "part=2/2" not in caplog.text and "123:test" not in caplog.text


def test_media_normalization_largest_photo_and_utf16_hashtags() -> None:
    """Photo variants represent one item; entities after emoji use UTF-16 offsets."""
    caption = "😀 [资源] a.b-c_d #tag1 #tag1 #中文"
    entities = []
    position = 0
    for tag in ("#tag1", "#tag1", "#中文"):
        start = caption.index(tag, position)
        offset = len(caption[:start].encode("utf-16-le")) // 2
        entities.append(MessageEntity("hashtag", offset, len(tag.encode("utf-16-le")) // 2))
        position = start + len(tag)
    small = SimpleNamespace(file_id="small", file_unique_id="s", width=100, height=100, file_size=200)
    large = SimpleNamespace(file_id="large", file_unique_id="l", width=1000, height=1000, file_size=2000)
    event = normalize_update(update(text=None, caption=caption, caption_entities=entities,
                                    photo=(large, small), media_group_id="album",
                                    reply_to_message=SimpleNamespace(message_id=8)), "x", "bot")
    assert len(event.segments) == 1 and event.segments[0].kind == "image"
    data = event.segments[0].data
    assert data["file_id"] == "large" and data["size"] == 2000
    assert data["title"] == "😀 [资源] a.b-c_d"
    assert data["caption"] == caption and data["tags"] == ("tag1", "中文")
    assert data["media_group_id"] == "album" and data["mime_type"] == "image/jpeg"
    assert event.reply_context["reply_to_message_id"] == "8"


@pytest.mark.parametrize("kind", ["video", "document"])
def test_media_keeps_original_filename_and_literal_hash(kind: str) -> None:
    item = SimpleNamespace(file_id="f", file_unique_id="u", file_name="pack.tar.gz",
                           mime_type="application/gzip", file_size=42)
    event = normalize_update(update(text=None, caption="title #literal", **{kind: item}), "x", "bot")
    data = event.segments[0].data
    assert event.segments[0].kind == ("video" if kind == "video" else "file")
    assert data["title"] == "title #literal" and data["tags"] == ()
    assert data["name"] == "pack.tar.gz" and data["mime_type"] == "application/gzip"


@pytest.mark.parametrize("fields", [
    {"animation": object(), "document": object()}, {"sticker": object()},
    {"video_note": object()}, {"paid_media": object()}, {"live_photo": object()},
    {"voice": object()}, {"audio": object()},
])
def test_unsupported_media_ignored(fields: dict) -> None:
    assert normalize_update(update(text=None, **fields), "x", "bot") is None


def test_other_bot_addressed_caption_has_no_native_entry() -> None:
    item = SimpleNamespace(file_id="f", file_unique_id="u")
    assert normalize_update(update(text=None, caption="/tgsetu@other", document=item), "x", "bot") is None


def test_native_archive_gate_no_dispatch_fallthrough_or_double_dedup() -> None:
    async def run() -> None:
        handled = []
        router = dispatcher(feature_switches={"tgsetu": True})
        service = SimpleNamespace(handle=AsyncMock(return_value=True))
        adapter = TelegramAdapter(settings(), lambda event: handled.append(event), tgsetu=service,
                                  native_authorizer=router.authorize_native)
        context = SimpleNamespace(bot=SimpleNamespace(username="TestBot"))
        item = SimpleNamespace(file_id="f", file_unique_id="u")
        incoming = update(text=None, document=item)
        await adapter._on_update(incoming, context)
        await adapter._on_update(incoming, context)
        await adapter._on_update(update("/tgsetu@TestBot on", message_id=2), context)
        await adapter._on_update(update("/tgsetu@other on", message_id=3), context)
        await adapter._on_update(update("/tgsetu on", user=999, message_id=4), context)
        await adapter._on_update(update(text=None, document=item, kind="group", chat_id=-456, message_id=5), context)
        assert service.handle.await_count == 2 and handled == []
        assert service.handle.await_args_list[1].args[0].text == "/tgsetu on"
        assert not router.authorize_native(normalize_update(incoming, "test", "TestBot"), "tgsetu")
    asyncio.run(run())


def test_archive_disabled_command_guidance_and_silent_media() -> None:
    async def run() -> None:
        router = dispatcher()
        adapter = TelegramAdapter(settings(), router.dispatch_payload)
        adapter.send_reply = AsyncMock()
        context = SimpleNamespace(bot=SimpleNamespace(username="TestBot"))
        await adapter._on_update(update("/tgsetu on"), context)
        item = SimpleNamespace(file_id="f", file_unique_id="u")
        await adapter._on_update(update(text=None, document=item, message_id=2), context)
        assert adapter.send_reply.await_count == 1
        assert "unavailable" in adapter.send_reply.await_args.args[1]
        assert not router.router.eligible("tgsetu", "telegram")
        enabled = dispatcher(feature_switches={"tgsetu": True})
        assert "/tgsetu" in enabled.router.help("telegram")
        assert "/tgsetu" not in enabled.router.help("onebot")
        assert "/setu" not in enabled.router.help("telegram")
    asyncio.run(run())


@pytest.mark.parametrize("source_kind", ["valid", "remote", "relative", "outside", "symlink", "directory", "missing"])
def test_sdk_cache_path_validation(tmp_path: object, source_kind: str) -> None:
    async def run() -> None:
        cache = tmp_path / "cache"
        cache.mkdir()
        saved = cache / "file.mp4"
        saved.write_bytes(b"bytes")
        outside = tmp_path / "outside.mp4"
        outside.write_bytes(b"private")
        link = cache / "link.mp4"
        link.symlink_to(outside)
        paths = {"valid": str(saved), "remote": "https://api.telegram.org/file/botSECRET/a.mp4",
                 "relative": "file.mp4", "outside": str(outside), "symlink": str(link),
                 "directory": str(cache), "missing": str(cache / "missing")}
        retrieve = AsyncMock(return_value=SimpleNamespace(file_path=paths[source_kind]))
        service = SimpleNamespace(config=SimpleNamespace(cache_root=cache))
        adapter = TelegramAdapter(settings(telegram_local_mode=True), lambda event: None, tgsetu=service)
        adapter._application = SimpleNamespace(bot=SimpleNamespace(get_file=retrieve))
        if source_kind == "valid":
            assert await adapter.media_path({"file_id": "retrieve"}) == saved
        else:
            with pytest.raises((ValueError, OSError)):
                await adapter.media_path({"file_id": "retrieve"})
        assert retrieve.await_args.args == ("retrieve",)
        assert retrieve.await_args.kwargs["read_timeout"] == 300
    asyncio.run(run())


def test_media_gateway_requires_explicit_local_mode_before_sdk() -> None:
    async def run() -> None:
        retrieve = AsyncMock()
        adapter = TelegramAdapter(settings(), lambda event: None, tgsetu=SimpleNamespace())
        adapter._application = SimpleNamespace(bot=SimpleNamespace(get_file=retrieve))
        with pytest.raises(ValueError):
            await adapter.media_path({"file_id": "f"})
        retrieve.assert_not_awaited()
    asyncio.run(run())


@pytest.mark.parametrize("directory_link", [False, True])
def test_sdk_cache_alias_preserves_symlink_rejection(tmp_path: object, directory_link: bool) -> None:
    """An in-cache link must not disappear before the bounded source opener."""
    async def run() -> None:
        cache = tmp_path / "cache"
        real = cache / "real"
        real.mkdir(parents=True)
        saved = real / "file.mp4"
        saved.write_bytes(b"bytes")
        alias = cache / "alias"
        alias.symlink_to(real if directory_link else saved, target_is_directory=directory_link)
        source = alias / "file.mp4" if directory_link else alias
        config = TgSetuConfig(cache_root=cache, save_root=tmp_path / "archive")
        service = SimpleNamespace(config=config)
        adapter = TelegramAdapter(settings(telegram_local_mode=True), lambda event: None, tgsetu=service)
        retrieve = AsyncMock(return_value=SimpleNamespace(file_path=str(source)))
        adapter._application = SimpleNamespace(bot=SimpleNamespace(get_file=retrieve))
        location = await adapter.media_path({"file_id": "retrieve"})
        assert location == source
        with pytest.raises(OSError):
            TgSetuFileSaver(config).prepare(location, 100)
        assert not config.save_root.exists()
    asyncio.run(run())


def test_archive_notice_quotes_source_and_returns_receipt() -> None:
    async def run() -> None:
        send = AsyncMock(return_value=SimpleNamespace(message_id=17))
        adapter = TelegramAdapter(settings(), lambda event: None)
        adapter._application = SimpleNamespace(bot=SimpleNamespace(send_message=send))
        assert await adapter.send_notice("123", "saved", "6") == "17"
        assert send.await_args.kwargs["reply_parameters"].message_id == 6
        assert send.await_args.kwargs["parse_mode"] is None
    asyncio.run(run())


def test_archive_notice_queue_coalesces_and_bounds_without_claiming_receipts(caplog: object) -> None:
    async def run() -> None:
        adapter = TelegramAdapter(settings(), lambda event: None)
        adapter._notice_pending = {}
        adapter._notice_event = asyncio.Event()
        assert await adapter.send_notice("123", "accepted", "1") == ""
        assert await adapter.send_notice("123", "saved", "1") == ""
        assert list(adapter._notice_pending.values()) == ["saved"]
        for number in range(2, 257):
            await adapter.send_notice("123", "pending", str(number))
        with pytest.raises(ValueError):
            await adapter.send_notice("123", "secret-body", "257")
        assert len(adapter._notice_pending) == 256
        assert await adapter.send_notice("123", "final", "1") == ""
    with caplog.at_level(logging.WARNING, logger="kisara.telegram"):
        asyncio.run(run())
    assert "queue is full" in caplog.text and "secret-body" not in caplog.text


def test_archive_notice_retries_only_known_short_rejection(monkeypatch: object) -> None:
    monkeypatch.setenv("PTB_TIMEDELTA", "true")
    async def run() -> None:
        adapter = TelegramAdapter(settings(), lambda event: None)
        send = AsyncMock(side_effect=[RetryAfter(2), SimpleNamespace(message_id=9)])
        sleep = AsyncMock()
        monkeypatch.setattr("kisara.bot.adapters.telegram.asyncio.sleep", sleep)
        adapter._application = SimpleNamespace(bot=SimpleNamespace(send_message=send))
        assert await adapter.send_notice("123", "saved", "6") == "9"
        assert send.await_count == 2 and sleep.await_args.args == (2.0,)
        for error, expected in ((RetryAfter(60), 1), (RetryAfter(1), 3), (NetworkError("secret"), 1)):
            send.side_effect = error
            send.reset_mock()
            with pytest.raises(type(error)):
                await adapter.send_notice("123", "saved", "6")
            assert send.await_count == expected
    asyncio.run(run())


def test_archive_notice_chunk_retry_keeps_confirmed_prefix(monkeypatch: object) -> None:
    monkeypatch.setenv("PTB_TIMEDELTA", "true")
    async def run() -> None:
        adapter = TelegramAdapter(settings(), lambda event: None)
        send = AsyncMock(side_effect=[SimpleNamespace(message_id=10), RetryAfter(1),
                                     SimpleNamespace(message_id=11)])
        monkeypatch.setattr("kisara.bot.adapters.telegram.asyncio.sleep", AsyncMock())
        adapter._application = SimpleNamespace(bot=SimpleNamespace(send_message=send))
        assert await adapter.send_notice("123", "a" * 4096 + "tail", "6") == "11"
        assert [call.kwargs["text"] for call in send.await_args_list] == ["a" * 4096, "tail", "tail"]
    asyncio.run(run())
