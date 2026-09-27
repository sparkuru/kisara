"""Check HTML parsing, dated caches, and daily-news command delivery."""

import base64
import io
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import Event
from typing import Callable, Optional

import pytest
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from kisara.application.services.daily_news import (
    PNG_LAYOUT_VERSION, SOURCE_URL, DailyNews, DailyPage, _page_for_today,
)
from kisara.bot.contracts import MessageEvent, MessageSegment, OutgoingMessage
from kisara.bot.dispatcher import Dispatcher
from kisara.infrastructure.integrations.http import RemoteServiceError


class FakeReader:
    """Track calls to the LyToday HTML page."""

    def __init__(self, html: str) -> None:
        """Keep one source page."""

        self.html = html
        self.calls = 0

    def get_text(self, url: str) -> str:
        """Return the configured HTML and record its URL."""

        assert url == SOURCE_URL
        self.calls += 1
        return self.html


def _html(month_day: str = "9月24日") -> str:
    """Build a small page with the same relevant markup as LyToday."""

    items = "".join("<li>{}、Headline {}</li>".format(i, i) for i in range(1, 15))
    items += '<li><a href="https://example.com/?a=1&amp;b=2">15、Linked &amp; final</a></li>'
    return (
        '<div id="lylme"><header><p>2026</p><h2>{}</h2></header>'
        '<main><h1><i>「60秒读懂世界」</i></h1><ul>{}</ul>'
        '<h1>「实时热搜」<a>完整榜单&gt;</a></h1>'
        '<h2><span>「百度热搜」</span><a>更多&gt;</a></h2>'
        '<table><tr><td class="hot h1">1.</td><td class="hot h2">'
        '<a>Search &amp; trend</a></td><td class="hot h3">100w</td></tr></table>'
        '<h2>「微博热搜」</h2><table><tr><td class="hot h2">Other trend</td></tr></table>'
        '<h1>「历史上的今天」</h1><ul><li><span>1959</span>·<a>Hall built</a></li></ul>'
        '<h1>「今日黄历」</h1><div class="huangli">'
        '<div id="md">Lunar day</div><div class="nayin"><b>Five elements</b>'
        '<i>Earth</i></div><div id="yi"><b>Good</b><i>Travel</i><i>Study</i></div>'
        '</div><h1>「每日一语」</h1><p>A daily saying.</p>'
        '</main></div>'
    ).format(month_day, items)


def _png() -> bytes:
    """Make a valid image for the cache boundary."""

    output = io.BytesIO()
    metadata = PngInfo()
    metadata.add_text("kisara_layout", PNG_LAYOUT_VERSION)
    Image.new("RGB", (2, 2), "white").save(output, format="PNG", pnginfo=metadata)
    return output.getvalue()


def _service(
    tmp_path: Path, reader: FakeReader, cache_days: int = 7,
    renderer: Optional[Callable[[date, DailyPage], bytes]] = None,
) -> DailyNews:
    """Build a deterministic service with isolated PNG and HTML caches."""

    return DailyNews(
        cache_dir=tmp_path / "daily-news", cache_days=cache_days, reader=reader,
        clock=lambda: datetime(2026, 9, 24, 8, tzinfo=timezone(timedelta(hours=8))),
        renderer=renderer or (lambda day, page: _png()),
        temp_dir=tmp_path / "raw-html",
    )


def _event(text: str, message_id: str, engine: str = "onebot") -> MessageEvent:
    """Build an allowed message for news routing."""

    return MessageEvent(
        engine=engine, instance_id="test", message_id=message_id,
        conversation_kind="private", conversation_id="user", sender_id="user",
        segments=(MessageSegment("text", {"text": text}),), reply_context={},
    )


def test_html_parser_keeps_the_page_sections_in_order() -> None:
    """Linked text should decode and each visible section should be retained."""

    page = _page_for_today(_html(), date(2026, 9, 24))

    assert len(page.headlines) == 15
    assert page.headlines[0] == "1、Headline 1"
    assert page.headlines[-1] == "15、Linked & final"
    assert page.hot_sections == (
        ("百度热搜", ("Search & trend",)),
        ("微博热搜", ("Other trend",)),
    )
    assert page.history == ("1959·Hall built",)
    assert page.calendar == ("Lunar day", "Five elements Earth", "Good Travel Study")
    assert page.quote == "A daily saying."


def test_daily_news_reuses_dated_image_and_prunes_expired_files(tmp_path: Path) -> None:
    """A second request should use the saved PNG without calling the site."""

    reader = FakeReader(_html())
    service = _service(tmp_path, reader, cache_days=2)
    cache = tmp_path / "daily-news"
    cache.mkdir()
    (cache / "20260922.png").write_bytes(_png())
    (cache / "20260923.png").write_bytes(_png())
    raw = tmp_path / "raw-html"
    raw.mkdir(mode=0o700)
    (raw / "20260923.html").write_text(_html("9月23日"))

    first = service.get()
    second = service.get()

    assert first.image_path == cache / "20260924.png"
    assert second.image_path == first.image_path
    assert first.image_path.read_bytes() == _png()
    assert (tmp_path / "raw-html" / "20260924.html").read_text() == _html()
    assert not (raw / "20260923.html").exists()
    assert reader.calls == 1
    assert not (cache / "20260922.png").exists()
    assert (cache / "20260923.png").exists()


def test_old_layout_image_is_regenerated_from_cached_html(tmp_path: Path) -> None:
    """An earlier headline-only PNG must not hide the expanded page image."""

    reader = FakeReader(_html())
    service = _service(tmp_path, reader)
    cache = tmp_path / "daily-news"
    cache.mkdir()
    output = io.BytesIO()
    Image.new("RGB", (2, 2), "white").save(output, format="PNG")
    (cache / "20260924.png").write_bytes(output.getvalue())

    result = service.get()

    assert result.image_path.read_bytes() == _png()
    assert reader.calls == 1


def test_page_requires_exactly_fifteen_headlines() -> None:
    """Extra list items should not be silently dropped before validation."""

    html = _html().replace("</ul>", "<li>16、Extra headline</li></ul>", 1)

    with pytest.raises(RemoteServiceError, match="invalid headlines"):
        _page_for_today(html, date(2026, 9, 24))


def test_daily_news_rejects_stale_html_without_caching_it(tmp_path: Path) -> None:
    """A late page update must not be stored under today's filename."""

    reader = FakeReader(_html("9月23日"))
    service = _service(tmp_path, reader)

    with pytest.raises(RemoteServiceError, match="not yet available"):
        service.get()
    assert not (tmp_path / "daily-news" / "20260924.png").exists()
    assert not (tmp_path / "raw-html" / "20260924.html").exists()


def test_render_retry_uses_temporary_html_without_refetch(tmp_path: Path) -> None:
    """A renderer failure can retry from the validated HTML on disk."""

    reader = FakeReader(_html())

    def fail_render(day: date, page: DailyPage) -> bytes:
        """Simulate a transient render failure."""

        raise RemoteServiceError("Renderer is unavailable.")

    with pytest.raises(RemoteServiceError, match="Renderer is unavailable"):
        _service(tmp_path, reader, renderer=fail_render).get()

    result = _service(tmp_path, reader).get()

    assert result.image_path.is_file()
    assert reader.calls == 1


def test_news_aliases_send_the_cached_image(tmp_path: Path) -> None:
    """Chinese and English triggers should send a real PNG through OneBot."""

    reader = FakeReader(_html())
    dispatcher = Dispatcher(
        allowed_users=frozenset({"user"}), groups_enabled=False,
        allowed_groups=frozenset(), daily_news=_service(tmp_path, reader),
    )

    for index, alias in enumerate(("新闻", "每日新闻", "news", "/news")):
        reply = dispatcher.dispatch_payload(_event(alias, str(index)))
        assert isinstance(reply, OutgoingMessage)
        assert len(reply.image_urls) == 1
        assert base64.b64decode(reply.image_urls[0].split("base64://", 1)[1]) == _png()
    assert reader.calls == 1

    official = dispatcher.dispatch_payload(_event("每日新闻", "official", "official"))
    assert isinstance(official, str)
    assert SOURCE_URL in official


def test_group_news_word_works_without_chat_enabled(tmp_path: Path) -> None:
    """An allowed group's plain news trigger should pass command access rules."""

    reader = FakeReader(_html())
    dispatcher = Dispatcher(
        allowed_users=frozenset({"user"}), groups_enabled=True,
        allowed_groups=frozenset({"group"}), daily_news=_service(tmp_path, reader),
    )
    event = MessageEvent(
        engine="onebot", instance_id="test", message_id="group-news",
        conversation_kind="group", conversation_id="group", sender_id="user",
        segments=(MessageSegment("text", {"text": "news"}),), reply_context={},
    )

    assert isinstance(dispatcher.dispatch_payload(event), OutgoingMessage)


def test_clear_command_removes_both_layers_and_refetches(tmp_path: Path) -> None:
    """Clearing should preserve other files and regenerate from fresh source."""

    reader = FakeReader(_html())
    rendered = []

    def render(day: date, page: DailyPage) -> bytes:
        """Record the content used for each image."""

        rendered.append(page.headlines[0])
        return _png()

    service = _service(tmp_path, reader, renderer=render)
    dispatcher = Dispatcher(
        allowed_users=frozenset({"user"}), groups_enabled=False,
        allowed_groups=frozenset(), daily_news=service,
    )
    image = service.get().image_path
    raw = tmp_path / "raw-html" / "20260924.html"
    preserved = []
    for directory, extension in ((image.parent, "png"), (raw.parent, "html")):
        for name in ("20260923", "20260925", "unrelated"):
            path = directory / "{}.{}".format(name, extension)
            path.write_bytes(b"preserve")
            preserved.append(path)

    result = dispatcher.dispatch_result(_event("清除新闻缓存", "clear"))

    assert result.status == "handled"
    assert result.reply == "已清除当日新闻缓存，下次获取新闻时将重新生成。"
    assert not result.image_urls
    assert not image.exists() and not raw.exists()
    assert all(path.read_bytes() == b"preserve" for path in preserved)
    assert reader.calls == 1 and len(rendered) == 1
    reader.html = _html().replace("Headline 1</li>", "Updated headline</li>")

    refreshed = dispatcher.dispatch_payload(_event("/news", "refresh"))

    assert isinstance(refreshed, OutgoingMessage)
    assert base64.b64decode(refreshed.image_urls[0].split("base64://", 1)[1]) == _png()
    assert reader.calls == 2
    assert rendered == ["1、Headline 1", "1、Updated headline"]
    assert raw.read_text() == reader.html


@pytest.mark.parametrize("layer", ("none", "png", "html", "both"))
def test_clear_cache_is_empty_or_idempotent_without_generation(
    tmp_path: Path, layer: str,
) -> None:
    """Each cache layer is optional and clearing must never generate content."""

    reader = FakeReader(_html())

    def no_render(day: date, page: DailyPage) -> bytes:
        """Fail if clearing invokes the renderer."""

        pytest.fail("Clearing must not render news")

    service = _service(tmp_path, reader, renderer=no_render)
    cache = tmp_path / "daily-news"
    raw = tmp_path / "raw-html"
    if layer in {"png", "both"}:
        cache.mkdir()
        (cache / "20260924.png").write_bytes(_png())
    if layer in {"html", "both"}:
        raw.mkdir(mode=0o700)
        (raw / "20260924.html").write_text(_html())

    assert service.clear_cache() == (layer != "none")
    assert not service.clear_cache()
    assert cache.exists() == (layer in {"png", "both"})
    assert raw.exists() == (layer in {"html", "both"})
    assert not (cache / "20260924.png").exists()
    assert not (raw / "20260924.html").exists()
    assert reader.calls == 0


def test_clear_cache_selects_the_china_standard_time_day(tmp_path: Path) -> None:
    """The China day can differ from the injected UTC clock's date."""

    cache = tmp_path / "daily-news"
    raw = tmp_path / "raw-html"
    cache.mkdir()
    raw.mkdir(mode=0o700)
    for directory, extension in ((cache, "png"), (raw, "html")):
        (directory / "20260924.{}".format(extension)).write_bytes(b"UTC day")
        (directory / "20260925.{}".format(extension)).write_bytes(b"China day")
    reader = FakeReader(_html())
    service = DailyNews(
        cache_dir=cache, temp_dir=raw, reader=reader,
        clock=lambda: datetime(2026, 9, 24, 20, tzinfo=timezone.utc),
    )

    assert service.clear_cache()
    assert (cache / "20260924.png").read_bytes() == b"UTC day"
    assert (raw / "20260924.html").read_bytes() == b"UTC day"
    assert not (cache / "20260925.png").exists()
    assert not (raw / "20260925.html").exists()
    assert reader.calls == 0


def test_clear_waits_for_cache_generation(tmp_path: Path) -> None:
    """An in-progress renderer must finish before its caches can be cleared."""

    rendering = Event()
    release = Event()
    clearing = Event()
    cleared = Event()

    def render(day: date, page: DailyPage) -> bytes:
        """Pause generation while the clear request is submitted."""

        rendering.set()
        assert release.wait(5)
        return _png()

    service = _service(tmp_path, FakeReader(_html()), renderer=render)

    def clear() -> bool:
        """Record the lifetime of the concurrent clearing request."""

        clearing.set()
        result = service.clear_cache()
        cleared.set()
        return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        generation = pool.submit(service.get)
        try:
            assert rendering.wait(5)
            removal = pool.submit(clear)
            assert clearing.wait(5)
            assert not cleared.wait(0.05)
        finally:
            release.set()
        generated = generation.result(timeout=5)
        assert removal.result(timeout=5)

    assert not generated.image_path.exists()
    assert not (tmp_path / "raw-html" / "20260924.html").exists()


@pytest.mark.parametrize("unsafe", ("mode", "owner", "symlink", "file"))
def test_clear_rejects_unsafe_temporary_cache_before_deletion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unsafe: str,
) -> None:
    """Directory safety checks must apply to deletion as well as HTML reads."""

    reader = FakeReader(_html())
    service = _service(tmp_path, reader)
    image = service.get().image_path
    raw = tmp_path / "raw-html"
    if unsafe == "mode":
        raw.chmod(0o777)
    elif unsafe == "owner":
        owner = os.getuid()
        monkeypatch.setattr(os, "getuid", lambda: owner + 1)
    else:
        retained = tmp_path / "retained-html"
        raw.rename(retained)
        if unsafe == "symlink":
            raw.symlink_to(retained, target_is_directory=True)
        else:
            raw.write_bytes(b"not a directory")
    dispatcher = Dispatcher(
        allowed_users=frozenset({"user"}), groups_enabled=False,
        allowed_groups=frozenset(), daily_news=service,
    )

    result = dispatcher.dispatch_result(_event("清除新闻缓存", "unsafe"))

    assert result.status == "error"
    assert result.reply == "Daily news temporary cache is unsafe."
    assert image.read_bytes() == _png()
    html_dir = retained if unsafe in {"symlink", "file"} else raw
    assert (html_dir / "20260924.html").read_text() == _html()
    assert reader.calls == 1


@pytest.mark.parametrize("failed_layer", ("png", "html"))
def test_clear_deletion_failure_returns_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failed_layer: str,
) -> None:
    """A filesystem failure must never produce a successful confirmation."""

    service = _service(tmp_path, FakeReader(_html()))
    image = service.get().image_path
    raw = tmp_path / "raw-html" / "20260924.html"
    failed = image if failed_layer == "png" else raw
    unlink = Path.unlink

    def fail_unlink(path: Path, *args: object, **kwargs: object) -> None:
        """Simulate a failure containing a private path in its diagnostics."""

        if path == failed:
            raise PermissionError("private storage path")
        unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_unlink)
    dispatcher = Dispatcher(
        allowed_users=frozenset({"user"}), groups_enabled=False,
        allowed_groups=frozenset(), daily_news=service,
    )

    result = dispatcher.dispatch_result(_event("清除新闻缓存", "failed"))

    assert result.status == "error"
    assert result.reply == "Daily news cache could not be cleared."
    assert failed.exists()
    if failed_layer == "html":
        assert not image.exists()
    monkeypatch.setattr(Path, "unlink", unlink)

    retried = dispatcher.dispatch_result(_event("清除新闻缓存", "retry"))

    assert retried.status == "handled"
    assert retried.reply == "已清除当日新闻缓存，下次获取新闻时将重新生成。"
    assert not image.exists() and not raw.exists()


@pytest.mark.parametrize(
    "sender,kind,group,groups_enabled",
    (("other", "private", "user", True),
     ("user", "group", "group", False),
     ("user", "group", "other-group", True)),
)
def test_clear_access_rejections_preserve_cache(
    tmp_path: Path, sender: str, kind: str, group: str, groups_enabled: bool,
) -> None:
    """Rejected senders and group settings must prevent deletion."""

    reader = FakeReader(_html())
    service = _service(tmp_path, reader)
    image = service.get().image_path
    raw = tmp_path / "raw-html" / "20260924.html"
    dispatcher = Dispatcher(
        allowed_users=frozenset({"user"}), groups_enabled=groups_enabled,
        allowed_groups=frozenset({"group"}), daily_news=service,
    )
    event = replace(
        _event("清除新闻缓存", "denied"), sender_id=sender,
        conversation_kind=kind, conversation_id=group,
    )

    assert dispatcher.dispatch_result(event).status == "unhandled"
    assert image.read_bytes() == _png()
    assert raw.read_text() == _html()
    assert reader.calls == 1


@pytest.mark.parametrize(
    "phrase,kind,engine",
    (("清除新闻缓存", "private", "onebot"),
     ("  # 清除新闻缓存  ", "group", "onebot"),
     ("清除新闻缓存", "private", "official")),
)
def test_clear_aliases_reply_and_duplicate_events_preserve_refreshed_cache(
    tmp_path: Path, phrase: str, kind: str, engine: str,
) -> None:
    """Allowed aliases work without chat and duplicate clears stay silent."""

    reader = FakeReader(_html())
    service = _service(tmp_path, reader)
    dispatcher = Dispatcher(
        allowed_users=frozenset({"user"}), groups_enabled=True,
        allowed_groups=frozenset({"group"}), daily_news=service,
    )
    event = replace(
        _event(phrase, "clear", engine), conversation_kind=kind,
        conversation_id="group" if kind == "group" else "user",
    )

    result = dispatcher.dispatch_result(event)

    assert result.status == "handled"
    assert result.reply == "当日没有新闻缓存可清除。"
    assert not result.image_urls
    assert reader.calls == 0
    image = service.get().image_path
    duplicate = dispatcher.dispatch_result(event)
    assert duplicate.status == "unhandled" and duplicate.reply is None
    assert image.read_bytes() == _png()
    assert (tmp_path / "raw-html" / "20260924.html").read_text() == _html()


@pytest.mark.parametrize("phrase", ("清除新闻缓存 all", "#清除新闻缓存 all", "/news-clear all"))
def test_clear_command_rejects_arguments_without_deletion(
    tmp_path: Path, phrase: str,
) -> None:
    """Extra arguments are a command error rather than another chat phrase."""

    service = _service(tmp_path, FakeReader(_html()))
    image = service.get().image_path
    dispatcher = Dispatcher(
        allowed_users=frozenset({"user"}), groups_enabled=False,
        allowed_groups=frozenset(), daily_news=service,
    )

    result = dispatcher.dispatch_result(_event(phrase, "arguments"))

    assert result.status == "error" and result.reason == "Invalid command arguments."
    assert image.read_bytes() == _png()
    assert (tmp_path / "raw-html" / "20260924.html").read_text() == _html()


@pytest.mark.parametrize("phrase", ("清除新闻缓存一下", "#清除新闻缓存一下"))
def test_clear_phrase_with_attached_suffix_is_not_a_command(
    tmp_path: Path, phrase: str,
) -> None:
    """Ordinary text that extends the exact trigger must not delete files."""

    service = _service(tmp_path, FakeReader(_html()))
    image = service.get().image_path
    dispatcher = Dispatcher(
        allowed_users=frozenset({"user"}), groups_enabled=False,
        allowed_groups=frozenset(), daily_news=service,
    )

    result = dispatcher.dispatch_result(_event(phrase, "suffix"))

    assert result.status == "unhandled"
    assert image.read_bytes() == _png()
    assert (tmp_path / "raw-html" / "20260924.html").read_text() == _html()


@pytest.mark.parametrize("enabled", (False, True))
def test_help_advertises_clearing_only_when_news_is_enabled(
    tmp_path: Path, enabled: bool,
) -> None:
    """The help command must agree with the assembled news capabilities."""

    service = _service(tmp_path, FakeReader(_html())) if enabled else None
    dispatcher = Dispatcher(
        allowed_users=frozenset({"user"}), groups_enabled=False,
        allowed_groups=frozenset(), daily_news=service,
    )

    result = dispatcher.dispatch_result(_event("/help", "help"))

    assert result.status == "handled"
    assert ("清除新闻缓存" in result.reply) == enabled
