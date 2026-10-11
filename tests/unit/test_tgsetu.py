"""Durable Telegram opt-in, albums, partial retry and crash recovery tests."""

import asyncio
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
import time
from typing import Any, Callable, Dict, List, Mapping, Tuple

import pytest

from kisara.application.services.tgsetu import TgSetu
from kisara.bot.contracts import MessageEvent, MessageSegment
from kisara.config.tgsetu import TgSetuConfig
from kisara.infrastructure.persistence.tgsetu import TgSetuStore
from kisara.infrastructure.persistence.tgsetu_files import TgSetuCancelled


class FakeGateway:
    """Canonical local paths and captured authorized notices, without a SDK."""

    def __init__(self) -> None:
        """Initialize per-file retrieval evidence and response fixtures."""
        self.paths: Dict[str, Path] = {}
        self.calls: List[str] = []
        self.notices: List[Tuple[str, str, str]] = []
        self.block = False
        self.entered = asyncio.Event()
        self.fail_notices = False

    async def media_path(self, media: Mapping[str, Any]) -> Path:
        """Observe retrieval and optionally simulate cancelled getFile."""
        identifier = str(media["file_id"])
        self.calls.append(identifier)
        self.entered.set()
        if self.block:
            await asyncio.Future()
        return self.paths[identifier]

    async def send_notice(self, chat_id: str, text: str,
                          reply_to_message_id: str = "") -> str:
        """Capture confirmed synthetic replies without real credentials."""
        if self.fail_notices:
            raise RuntimeError("synthetic token-bearing URL must not leak")
        self.notices.append((chat_id, text, reply_to_message_id))
        return str(1000 + len(self.notices))


def _config(tmp_path: Path, **changes: Any) -> TgSetuConfig:
    """Use tiny album timers and isolated local fixture directories."""
    config = replace(TgSetuConfig.disabled(), enabled=True, allowed_users=frozenset({"123"}),
                     cache_root=tmp_path / "cache", save_root=tmp_path / "archive",
                     album_quiet_seconds=0.08, album_max_wait_seconds=0.2)
    return replace(config, **changes)


def _event(message_id: str, text: str = "", media: Tuple[MessageSegment, ...] = ()) -> MessageEvent:
    """Create a normalized authorized private Telegram destination message."""
    segments = media + ((MessageSegment("text", {"text": text}),) if text else ())
    return MessageEvent("telegram", "personal", message_id, "private", "123", "123", segments, {})


def _media(file_id: str, kind: str = "image", title: str = "", caption: str = "",
           album: str = "", name: str = "", tags: Tuple[str, ...] = (), size: int = 0) -> MessageSegment:
    """Represent exactly one real media item, independent of SDK PhotoSize."""
    return MessageSegment(kind, {"file_id": file_id, "file_unique_id": "unique-" + file_id,
                                 "title": title, "caption": caption, "media_group_id": album,
                                 "name": name, "tags": tags, "size": size,
                                 "mime_type": "video/mp4" if kind == "video" else "image/jpeg"})


def _source(config: TgSetuConfig, gateway: FakeGateway, identifier: str,
            content: bytes = b"content") -> Path:
    """Place bytes only in the configured test Bot API cache."""
    source = config.cache_root / "bot" / identifier
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(content)
    gateway.paths[identifier] = source
    return source


def _rows(tmp_path: Path) -> List[Dict[str, Any]]:
    """Inspect observable durable outcomes using a separately opened database."""
    with sqlite3.connect(str(tmp_path / "state" / "tgsetu.sqlite3")) as database:
        database.row_factory = sqlite3.Row
        return [dict(row) for row in database.execute("SELECT * FROM members ORDER BY id")]


async def _until(predicate: Callable[[], bool]) -> None:
    """Wait for an actual outcome with a bounded failure deadline."""
    deadline = time.monotonic() + 4
    while not predicate():
        assert time.monotonic() < deadline, "Timed out waiting for archive outcome"
        await asyncio.sleep(0.01)


async def _stop(task: asyncio.Task) -> None:
    """Cancel and await the service owner to catch leaked work."""
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.parametrize("change", [
    {"sender_id": "999"}, {"conversation_kind": "group"}, {"engine": "onebot"},
    {"instance_id": "other"},
])
def test_denied_events_have_no_metadata_sdk_or_archive_effects(tmp_path: Path, change: Dict[str, str]) -> None:
    """Direct core calls cannot bypass the adapter's authorization gate."""
    async def scenario() -> None:
        """Reject both commands and media before SQLite construction."""
        config, gateway = _config(tmp_path), FakeGateway()
        service = TgSetu(config, str(tmp_path / "state"), "personal", frozenset({"123"}))
        for event in (_event("1", "/tgsetu on"), _event("2", media=(_media("a"),))):
            assert not await service.handle(replace(event, **change), gateway)
        assert not gateway.notices and not gateway.calls
        assert not (tmp_path / "state").exists() and not config.save_root.exists()
    asyncio.run(scenario())


@pytest.mark.parametrize("disabled", ["feature", "global", "feature-user"])
def test_disabled_and_empty_allowlists_are_inert(tmp_path: Path, disabled: str) -> None:
    """Enabling a feature never implies global or feature user permission."""
    async def scenario() -> None:
        """Attempt opt-in and worker startup without an effective allowed user."""
        config = _config(tmp_path)
        config = replace(config, enabled=False) if disabled == "feature" else config
        config = replace(config, allowed_users=frozenset()) if disabled == "feature-user" else config
        users = frozenset() if disabled == "global" else frozenset({"123"})
        service, gateway = TgSetu(config, str(tmp_path / "state"), "personal", users), FakeGateway()
        assert not await service.handle(_event("1", "/tgsetu on"), gateway)
        await service.run(gateway)
        assert not list(tmp_path.iterdir()) and not gateway.calls
    asyncio.run(scenario())


def test_off_on_restart_and_accepted_work_finishes_after_off(tmp_path: Path) -> None:
    """Activation persists; off ignores new media while existing files finish."""
    async def scenario() -> None:
        """Accept before launching workers, disable, then recover on restart."""
        config, gateway = _config(tmp_path), FakeGateway()
        _source(config, gateway, "accepted")
        service = TgSetu(config, str(tmp_path / "state"), "personal", frozenset({"123"}))
        assert not await service.handle(_event("1", media=(_media("ignored"),)), gateway)
        assert not (tmp_path / "state").exists()
        assert await service.handle(_event("2", "/tgsetu on"), gateway)
        service = TgSetu(config, str(tmp_path / "state"), "personal", frozenset({"123"}))
        await service.handle(_event("3", "/tgsetu"), gateway)
        assert "is on" in gateway.notices[-1][1]
        assert await service.handle(_event("4", media=(_media("accepted", title="archive", caption="archive"),)), gateway)
        await service.handle(_event("5", "/tgsetu off"), gateway)
        assert not await service.handle(_event("6", media=(_media("ignored"),)), gateway)
        task = asyncio.create_task(service.run(gateway))
        try:
            await _until(lambda: _rows(tmp_path)[0]["status"] == "saved")
            assert (config.save_root / "archive.jpg").read_bytes() == b"content"
            assert gateway.calls == ["accepted"]
            assert await service.handle(_event("4", media=(_media("accepted"),)), gateway) is False
        finally:
            await _stop(task)
        restarted = TgSetu(config, str(tmp_path / "state"), "personal", frozenset({"123"}))
        await restarted.handle(_event("7", "/tgsetu status"), gateway)
        assert "is off" in gateway.notices[-1][1]
    asyncio.run(scenario())


def test_distinct_messages_keep_captions_and_chat_scoped_dedup(tmp_path: Path) -> None:
    """A reused numeric source ID in another chat is an independent file."""
    async def scenario() -> None:
        """Save separate descriptions and replay an already accepted source."""
        config = _config(tmp_path, allowed_users=frozenset({"123", "456"}))
        gateway = FakeGateway()
        for item in ("first", "second", "other-chat"):
            _source(config, gateway, item, item.encode())
        service = TgSetu(config, str(tmp_path / "state"), "personal", frozenset({"123", "456"}))
        await service.handle(_event("1", "/tgsetu on"), gateway)
        await service.handle(replace(_event("1", "/tgsetu on"), sender_id="456", conversation_id="456"), gateway)
        first = _event("2", media=(_media("first", title="first.title", caption="first.title"),))
        second = _event("3", media=(_media("second", title="second.title", caption="second.title"),))
        other = replace(_event("2", media=(_media("other-chat", title="other", caption="other"),)),
                        sender_id="456", conversation_id="456")
        for event in (first, second, first, other):
            assert await service.handle(event, gateway)
        assert len(_rows(tmp_path)) == 3
        task = asyncio.create_task(service.run(gateway))
        try:
            await _until(lambda: all(row["status"] == "saved" for row in _rows(tmp_path)))
            assert sorted(path.name for path in config.save_root.iterdir()) == ["first.title.jpg", "other.jpg", "second.title.jpg"]
            assert sorted(gateway.calls) == ["first", "other-chat", "second"]
        finally:
            await _stop(task)
    asyncio.run(scenario())


def test_album_caption_order_late_member_and_frozen_ordinals(tmp_path: Path) -> None:
    """Initial IDs order names; later lower IDs append without renumbering."""
    async def scenario() -> None:
        """Receive an out-of-order album with a later caption, then append."""
        config, gateway = _config(tmp_path), FakeGateway()
        for item in ("a", "b", "c"):
            _source(config, gateway, item, item.encode())
        service = TgSetu(config, str(tmp_path / "state"), "personal", frozenset({"123"}))
        await service.handle(_event("1", "/tgsetu on"), gateway)
        await service.handle(_event("20", media=(_media("b", "video", title="Shared", caption="Shared #tag",
                                                       tags=("tag",), album="album"),)), gateway)
        await service.handle(_event("10", media=(_media("a", album="album"),)), gateway)
        task = asyncio.create_task(service.run(gateway))
        try:
            await _until(lambda: len(_rows(tmp_path)) == 2 and all(row["status"] == "saved" for row in _rows(tmp_path)))
            first = config.save_root / "Shared-001-@tag.jpg"
            assert first.exists() and (config.save_root / "Shared-002-@tag.mp4").exists()
            inode = first.stat().st_ino
            await service.handle(_event("5", media=(_media("c", title="Late", caption="Late #new",
                                                          tags=("new",), album="album"),)), gateway)
            await _until(lambda: len(_rows(tmp_path)) == 3 and all(row["status"] == "saved" for row in _rows(tmp_path)))
            assert first.stat().st_ino == inode
            assert (config.save_root / "Shared-003-@tag.jpg").read_bytes() == b"c"
            assert not any("Late" in path.name for path in config.save_root.iterdir())
            assert any("1 logical unit; received 3 Telegram message(s), 3 file(s)" in notice[1]
                       for notice in gateway.notices)
        finally:
            await _stop(task)
    asyncio.run(scenario())


def test_captionless_album_keeps_fallback_after_late_caption(tmp_path: Path) -> None:
    """A late caption is metadata; already chosen names remain stable."""
    async def scenario() -> None:
        """Complete the initial window without any caption, then append text."""
        config, gateway = _config(tmp_path), FakeGateway()
        _source(config, gateway, "a")
        _source(config, gateway, "b")
        service = TgSetu(config, str(tmp_path / "state"), "personal", frozenset({"123"}))
        await service.handle(_event("1", "/tgsetu on"), gateway)
        await service.handle(_event("2", media=(_media("a", album="empty", name="original.jpg"),)), gateway)
        task = asyncio.create_task(service.run(gateway))
        try:
            await _until(lambda: _rows(tmp_path)[0]["status"] == "saved")
            original = Path(_rows(tmp_path)[0]["saved_path"])
            assert original.name.startswith("tg-123-") and original.name.endswith("-001.jpg")
            await service.handle(_event("3", media=(_media("b", title="Late", caption="Late", album="empty"),)), gateway)
            await _until(lambda: len(_rows(tmp_path)) == 2 and _rows(tmp_path)[1]["status"] == "saved")
            assert (config.save_root / original.name.replace("-001.jpg", "-002.jpg")).exists()
            assert any("Late caption retained" in notice[1] for notice in gateway.notices)
        finally:
            await _stop(task)
    asyncio.run(scenario())


def test_partial_failure_explicit_retry_keeps_success_name_and_inode(tmp_path: Path) -> None:
    """A retry touches failed members only, even when the user's mode is off."""
    async def scenario() -> None:
        """Save one document, fail a sibling retrieval, then repair and retry."""
        config, gateway = _config(tmp_path), FakeGateway()
        _source(config, gateway, "a", b"first")
        service = TgSetu(config, str(tmp_path / "state"), "personal", frozenset({"123"}))
        await service.handle(_event("1", "/tgsetu on"), gateway)
        await service.handle(_event("2", media=(_media("a", "file", name="pack.tar.gz", album="pair",
                                                     title="Collection", caption="Collection #tag", tags=("tag",)),)), gateway)
        await service.handle(_event("3", media=(_media("b", "video", album="pair"),)), gateway)
        task = asyncio.create_task(service.run(gateway))
        try:
            await _until(lambda: [row["status"] for row in _rows(tmp_path)] == ["saved", "failed"])
            archive = config.save_root / "pack-Collection-@tag.tar.gz"
            inode = archive.stat().st_ino
            _source(config, gateway, "b", b"second")
            await service.handle(_event("4", "/tgsetu off"), gateway)
            await service.handle(_event("5", "/tgsetu retry 3"), gateway)
            await _until(lambda: all(row["status"] == "saved" for row in _rows(tmp_path)))
            assert archive.stat().st_ino == inode
            assert gateway.calls.count("a") == 1 and gateway.calls.count("b") == 2
            assert (config.save_root / "Collection-002-@tag.mp4").read_bytes() == b"second"
            await service.handle(_event("6", "/tgsetu retry 2"), gateway)
            assert "Queued 0" in gateway.notices[-1][1]
        finally:
            await _stop(task)
    asyncio.run(scenario())


@pytest.mark.parametrize("cap", ["file-bytes", "unit-bytes", "unit-files", "queue"])
def test_acceptance_caps_precede_sdk_and_preserve_accepted_siblings(tmp_path: Path, cap: str) -> None:
    """Rejected excess metadata never consumes archive or retrieval resources."""
    async def scenario() -> None:
        """Fill the chosen budget with a known source, then exceed it."""
        changes = {"max_file_bytes": 5, "max_unit_bytes": 8}
        if cap == "unit-files":
            changes["max_unit_files"] = 1
        if cap == "queue":
            changes["max_pending_files"] = 1
        config, gateway = _config(tmp_path, **changes), FakeGateway()
        service = TgSetu(config, str(tmp_path / "state"), "personal", frozenset({"123"}))
        await service.handle(_event("1", "/tgsetu on"), gateway)
        await service.handle(_event("2", media=(_media("a", album="pair", size=4),)), gateway)
        await service.handle(_event("3", media=(_media("b", album="pair", size=6 if cap == "file-bytes" else 5),)), gateway)
        assert len(_rows(tmp_path)) == 1 and not gateway.calls and not config.save_root.exists()
        assert "Not accepted" in gateway.notices[-1][1]
    asyncio.run(scenario())


def test_unknown_size_enforces_actual_unit_budget_and_stops_retrieval(tmp_path: Path) -> None:
    """Unknown sizes cannot bypass the cumulative logical-unit byte cap."""
    async def scenario() -> None:
        """Copy the first unknown source, then reject excess actual bytes."""
        config, gateway = _config(tmp_path, max_file_bytes=5, max_unit_bytes=5), FakeGateway()
        _source(config, gateway, "a", b"first")
        _source(config, gateway, "b", b"later")
        service = TgSetu(config, str(tmp_path / "state"), "personal", frozenset({"123"}))
        await service.handle(_event("1", "/tgsetu on"), gateway)
        for message_id, item in (("2", "a"), ("3", "b")):
            await service.handle(_event(message_id, media=(_media(item, album="pair"),)), gateway)
        task = asyncio.create_task(service.run(gateway))
        try:
            await _until(lambda: [row["status"] for row in _rows(tmp_path)] == ["saved", "failed"])
            assert len(list(config.save_root.iterdir())) == 1
            assert gateway.calls == ["a"]
        finally:
            await _stop(task)
    asyncio.run(scenario())


def test_publication_before_database_crash_reconciles_without_sdk(tmp_path: Path) -> None:
    """Prepared intent identifies an already synced file when a claim restarts."""
    async def scenario() -> None:
        """Seed the exact crash interval and restart the service owner."""
        config, gateway = _config(tmp_path), FakeGateway()
        store = TgSetuStore(str(tmp_path / "state"))
        media = dict(_media("unavailable", title="Recovered", caption="Recovered").data, kind="image")
        store.enqueue("personal", "123", "123", "2", [media], 1000, config)
        store.freeze_due("personal", 1000, config, lambda user: True)
        member = store.claim("personal", lambda user: True)
        assert member is not None
        content = b"published before DB completion"
        digest = hashlib.sha256(content).hexdigest()
        config.save_root.mkdir()
        candidate = config.save_root / json.loads(member["plan_json"])["name"]
        store.intent(member["id"], candidate.name, digest, len(content))
        candidate.write_bytes(content)
        inode = candidate.stat().st_ino
        service = TgSetu(config, str(tmp_path / "state"), "personal", frozenset({"123"}))
        task = asyncio.create_task(service.run(gateway))
        try:
            await _until(lambda: _rows(tmp_path)[0]["status"] == "saved")
            assert not gateway.calls and candidate.stat().st_ino == inode
            assert len(list(config.save_root.iterdir())) == 1
        finally:
            await _stop(task)
    asyncio.run(scenario())


def test_restart_rechecks_authorization_before_prepared_reconciliation(tmp_path: Path) -> None:
    """Persisted accepted jobs are inert when the submitting user loses access."""
    async def scenario() -> None:
        """Allow another user to run workers while the prior owner is denied."""
        config = _config(tmp_path, allowed_users=frozenset({"123", "456"}))
        gateway, store = FakeGateway(), TgSetuStore(str(tmp_path / "state"))
        store.enqueue("personal", "123", "123", "2", [dict(_media("a").data, kind="image")], time.time(), config)
        service = TgSetu(config, str(tmp_path / "state"), "personal", frozenset({"456"}))
        task = asyncio.create_task(service.run(gateway))
        try:
            await asyncio.sleep(0.15)
            assert _rows(tmp_path)[0]["status"] == "queued" and not gateway.calls
            assert not config.save_root.exists()
        finally:
            await _stop(task)
    asyncio.run(scenario())


def test_cancel_getfile_requeues_claim_and_worker_shutdown_is_owned(tmp_path: Path) -> None:
    """A blocked SDK call is cancelled; no file is partially published."""
    async def scenario() -> None:
        """Stop while retrieving, then reopen the durable queued record."""
        config, gateway = _config(tmp_path), FakeGateway()
        gateway.block = True
        service = TgSetu(config, str(tmp_path / "state"), "personal", frozenset({"123"}))
        await service.handle(_event("1", "/tgsetu on"), gateway)
        await service.handle(_event("2", media=(_media("a"),)), gateway)
        task = asyncio.create_task(service.run(gateway))
        await asyncio.wait_for(gateway.entered.wait(), 2)
        await _stop(task)
        assert _rows(tmp_path)[0]["status"] == "queued"
        assert not config.save_root.exists()
        assert not any(thread.name.startswith("tgsetu-copy") for thread in threading.enumerate())
    asyncio.run(scenario())


def test_cancel_thread_waits_for_cleanup_without_orphan_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cooperative cancellation joins the actual file worker before returning."""
    started, stopped = threading.Event(), threading.Event()

    def blocked_prepare(self: Any, source: Path, remaining: int,
                        stop: threading.Event = None) -> Any:
        """Model a bounded copier waiting for cooperative stop."""
        started.set()
        while not stop.wait(0.005):
            pass
        stopped.set()
        raise TgSetuCancelled("stopped")

    monkeypatch.setattr("kisara.application.services.tgsetu.TgSetuFileSaver.prepare", blocked_prepare)

    async def scenario() -> None:
        """Cancel a live thread and capture any unobserved future failures."""
        config, gateway = _config(tmp_path), FakeGateway()
        _source(config, gateway, "a")
        service = TgSetu(config, str(tmp_path / "state"), "personal", frozenset({"123"}))
        await service.handle(_event("1", "/tgsetu on"), gateway)
        await service.handle(_event("2", media=(_media("a"),)), gateway)
        errors = []
        asyncio.get_running_loop().set_exception_handler(lambda loop, context: errors.append(context))
        task = asyncio.create_task(service.run(gateway))
        await _until(started.is_set)
        await _stop(task)
        assert stopped.is_set() and not errors
        assert _rows(tmp_path)[0]["status"] == "queued"
        assert not any(thread.name.startswith("tgsetu-copy") for thread in threading.enumerate())
    asyncio.run(scenario())


def test_notice_failure_does_not_strand_or_replay_saved_file(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Saving is independent of bot reply failure and diagnostics stay bounded."""
    async def scenario() -> None:
        """Fail every notice while successfully publishing and checkpointing."""
        config, gateway = _config(tmp_path), FakeGateway()
        gateway.fail_notices = True
        _source(config, gateway, "a")
        service = TgSetu(config, str(tmp_path / "state"), "personal", frozenset({"123"}))
        await service.handle(_event("1", "/tgsetu on"), gateway)
        await service.handle(_event("2", media=(_media("a"),)), gateway)
        task = asyncio.create_task(service.run(gateway))
        try:
            await _until(lambda: _rows(tmp_path)[0]["status"] == "saved")
            assert gateway.calls == ["a"]
            assert "token-bearing" not in caplog.text and "Archive notice failed (RuntimeError)" in caplog.text
        finally:
            await _stop(task)
    asyncio.run(scenario())


def test_naming_failure_reports_without_getfile_and_retry_is_truthful(tmp_path: Path) -> None:
    """A failed immutable plan produces a terminal notice without a worker claim."""
    async def scenario() -> None:
        """Use mandatory tags too long for NAME_MAX and observe failed state."""
        config, gateway = _config(tmp_path), FakeGateway()
        service = TgSetu(config, str(tmp_path / "state"), "personal", frozenset({"123"}))
        await service.handle(_event("1", "/tgsetu on"), gateway)
        await service.handle(_event("2", media=(_media("a", caption="#longtag", tags=("x" * 300,)),)), gateway)
        task = asyncio.create_task(service.run(gateway))
        try:
            await _until(lambda: any("naming failure(s)" in notice[1] for notice in gateway.notices))
            assert _rows(tmp_path)[0]["status"] == "failed" and not gateway.calls
            assert "cannot be retried" in gateway.notices[-1][1]
            await service.handle(_event("3", "/tgsetu retry 2"), gateway)
            assert "Queued 0" in gateway.notices[-1][1] and "Naming failures require" in gateway.notices[-1][1]
            assert not config.save_root.exists()
        finally:
            await _stop(task)
    asyncio.run(scenario())


def test_initial_album_max_wait_freezes_even_without_quiet(tmp_path: Path) -> None:
    """Continuous arrivals cannot keep initial naming undecided indefinitely."""
    config = _config(tmp_path, album_quiet_seconds=1, album_max_wait_seconds=5)
    store = TgSetuStore(str(tmp_path / "state"))
    store.enqueue("personal", "123", "123", "2", [dict(_media("a", album="busy").data, kind="image")], 1000, config)
    store.enqueue("personal", "123", "123", "3", [dict(_media("b", album="busy").data, kind="image")], 1004.9, config)
    store.freeze_due("personal", 1004.999, config, lambda user: True)
    assert store.claim("personal", lambda user: True) is None
    store.freeze_due("personal", 1005, config, lambda user: True)
    first = store.claim("personal", lambda user: True)
    assert first is not None and first["message_id"] == "2"
    assert store.claim("personal", lambda user: True) is None


def test_foreign_instance_jobs_are_never_claimed_or_frozen(tmp_path: Path) -> None:
    """Restarted state for another instance does not grant retrieval access."""
    config = _config(tmp_path)
    store = TgSetuStore(str(tmp_path / "state"))
    store.enqueue("foreign", "123", "123", "2", [dict(_media("a").data, kind="image")], 1000, config)
    store.freeze_due("personal", 1000, config, lambda user: True)
    assert store.claim("personal", lambda user: True) is None
    assert _rows(tmp_path)[0]["plan_json"] == ""


def test_retry_selector_is_scoped_to_source_chat_and_sender(tmp_path: Path) -> None:
    """A permitted different user cannot requeue another user's failed media."""
    config = _config(tmp_path)
    store = TgSetuStore(str(tmp_path / "state"))
    store.enqueue("personal", "123", "123", "2", [dict(_media("a").data, kind="image")], 1000, config)
    store.freeze_due("personal", 1000, config, lambda user: True)
    first = store.claim("personal", lambda user: True)
    assert first is not None
    store.fail(first["id"], "Unavailable", 1001)
    assert store.retry("personal", "456", "456", "2", config, 1002) == 0
    assert _rows(tmp_path)[0]["status"] == "failed"
    assert store.retry("personal", "123", "123", "2", config, 1002) == 1


def test_pruning_retains_files_activation_and_live_jobs(tmp_path: Path) -> None:
    """Seven-day metadata retention never deletes archived bytes or active work."""
    config = _config(tmp_path)
    store = TgSetuStore(str(tmp_path / "state"))
    store.set_active("personal", "123", "123", True)
    store.enqueue("personal", "123", "123", "2", [dict(_media("a").data, kind="image")], 1000, config)
    store.freeze_due("personal", 1000, config, lambda user: True)
    first = store.claim("personal", lambda user: True)
    assert first is not None
    config.save_root.mkdir()
    archived = config.save_root / "retained.jpg"
    archived.write_bytes(b"bytes")
    store.complete(first["id"], {"path": str(archived), "size": 5, "sha256": "fake"}, 1000)
    store.enqueue("personal", "123", "123", "3", [dict(_media("b").data, kind="image")], 1000, config)
    store.prune(1000 + 8 * 86400)
    assert [row["message_id"] for row in _rows(tmp_path)] == ["3"]
    assert archived.read_bytes() == b"bytes" and store.is_active("personal", "123", "123")


@pytest.mark.parametrize("deadline", ["quiet", "maximum"])
def test_late_album_arrival_freezes_window_while_all_workers_are_stalled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, deadline: str,
) -> None:
    """Metadata deadlines hold even when all transfers are waiting for getFile."""
    current_time = [1000.0]
    monkeypatch.setattr("kisara.application.services.tgsetu.time.time", lambda: current_time[0])

    async def scenario() -> None:
        """Occupy both workers, append a post-deadline caption, then release."""
        class StalledGateway(FakeGateway):
            """Hold initial standalone retrievals while album metadata arrives."""

            def __init__(self) -> None:
                """Own a deterministic release signal for the saturated workers."""
                super().__init__()
                self.release = asyncio.Event()

            async def media_path(self, media: Mapping[str, Any]) -> Path:
                """Block only the two standalone jobs, not the eventual album."""
                identifier = str(media["file_id"])
                self.calls.append(identifier)
                if identifier in {"busy-a", "busy-b"}:
                    await self.release.wait()
                return self.paths[identifier]

        config = _config(tmp_path, workers=2, album_quiet_seconds=1, album_max_wait_seconds=5)
        gateway = StalledGateway()
        service = TgSetu(config, str(tmp_path / "state"), "personal", frozenset({"123"}))
        await service.handle(_event("1", "/tgsetu on"), gateway)
        for message_id, identifier in (("2", "busy-a"), ("3", "busy-b")):
            _source(config, gateway, identifier)
            await service.handle(_event(message_id, media=(_media(identifier),)), gateway)
        task = asyncio.create_task(service.run(gateway))
        try:
            await _until(lambda: len(gateway.calls) == 2)
            _source(config, gateway, "initial")
            await service.handle(_event("20", media=(_media("initial", album="delayed"),)), gateway)
            initial_members = 1
            if deadline == "maximum":
                for index in range(1, 7):
                    current_time[0] = 1000 + 0.8 * index
                    identifier = "initial-" + str(index)
                    _source(config, gateway, identifier)
                    await service.handle(_event(str(20 + index), media=(_media(identifier, album="delayed"),)), gateway)
                    initial_members += 1
            current_time[0] = 1001 if deadline == "quiet" else 1005
            _source(config, gateway, "late")
            await service.handle(_event("10", media=(_media("late", title="Late", caption="Late #new",
                                                           tags=("new",), album="delayed"),)), gateway)
            album_rows = [row for row in _rows(tmp_path) if row["message_id"] not in {"2", "3"}]
            assert all(row["plan_json"] for row in album_rows)
            assert [row["ordinal"] for row in album_rows] == list(range(1, initial_members + 2))
            initial_name = json.loads(album_rows[0]["plan_json"])["name"]
            late_name = json.loads(album_rows[-1]["plan_json"])["name"]
            assert initial_name.startswith("tg-123-") and initial_name.endswith("-001.jpg")
            assert late_name == initial_name.replace("-001.jpg", "-{:03d}.jpg".format(initial_members + 1))
            assert gateway.calls == ["busy-a", "busy-b"]
            gateway.release.set()
            await _until(lambda: all(row["status"] == "saved" for row in _rows(tmp_path)))
            assert (config.save_root / initial_name).exists() and (config.save_root / late_name).exists()
            assert any("Late caption retained" in notice[1] for notice in gateway.notices)
        finally:
            await _stop(task)
    asyncio.run(scenario())
