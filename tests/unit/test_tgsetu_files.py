"""Behavioral tests for flat naming, bounded copy and no-replace recovery."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
from pathlib import Path
import threading
import tracemalloc
from typing import Any, Dict

import pytest

from kisara.config.tgsetu import TgSetuConfig
from kisara.infrastructure.persistence.tgsetu_files import (
    TgSetuCancelled, TgSetuFileError, TgSetuFileSaver, naming_plan, render_name,
)


def _config(tmp_path: Path) -> TgSetuConfig:
    """Use separate cache and archive roots."""
    return replace(TgSetuConfig.disabled(), save_root=tmp_path / "archive", cache_root=tmp_path / "cache")


def _source(config: TgSetuConfig, name: str, content: bytes) -> Path:
    """Create a controlled local Bot API cache fixture."""
    source = config.cache_root / "bot" / name
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(content)
    return source


def _save(saver: TgSetuFileSaver, source: Path, plan: Dict[str, Any], timestamp: float = 1000) -> Dict[str, Any]:
    """Publish through a caller-owned durable-intent callback."""
    prepared = saver.prepare(source, 100 * 1024 ** 2)
    return saver.publish(prepared, plan, timestamp, lambda name, digest, size: None)


def test_caption_punctuation_tags_and_original_compound_suffix(tmp_path: Path) -> None:
    """The actual media suffix follows title and tags; dots are preserved."""
    title = "[xxxx] \u89c6\u9891\u8d44\u6e90_1080p-aaaa.bbbb.cccc"
    plan = naming_plan({"kind": "video", "mime_type": "video/mp4"}, title,
                       ("tag1", "tag2", "tag3", "tag1"), "fallback")
    assert plan["name"] == title + "-@tag1-@tag2-@tag3.mp4"
    plan = naming_plan({"kind": "file", "name": "pack.tar.gz"}, "Collection",
                       ("tag1", "tag2"), "fallback")
    assert plan["name"] == "pack-Collection-@tag1-@tag2.tar.gz"
    assert naming_plan({"kind": "file", "name": "pack.tar.gz"}, "", (), "fallback")["name"] == "pack.tar.gz"
    assert naming_plan({"kind": "image"}, "a/b\n c", ("t",), "fallback", 2)["name"] == "a b c-002-@t.jpg"


def test_long_unicode_name_preserves_suffixes_and_has_digest() -> None:
    """Truncate title in UTF-8 bytes while reserving all required suffixes."""
    plan = naming_plan({"kind": "file", "name": "pack.tar.gz"}, "\U0001f600" * 200,
                       ("tag1", "tag2"), "fallback", 12)
    assert len(plan["name"].encode("utf-8")) <= 255
    assert plan["name"].endswith("-012-@tag1-@tag2.tar.gz")
    assert render_name(plan, "20260101-010101-012345678901").endswith("-@tag1-@tag2.tar.gz")
    with pytest.raises(TgSetuFileError, match="suffixes"):
        naming_plan({"kind": "image"}, "title", ("t" * 300,), "fallback")


def test_atomic_publish_intent_precedes_visibility_and_same_content_reuses(tmp_path: Path) -> None:
    """No partial final file exists; equal bytes retain the existing inode."""
    config = _config(tmp_path)
    source = _source(config, "native", b"complete bytes")
    saver = TgSetuFileSaver(config)
    plan = naming_plan({"kind": "file", "name": "pack.zip"}, "Collection", ("tag",), "fallback")
    prepared = saver.prepare(source, 100)
    destination = config.save_root / plan["name"]
    assert not destination.exists()
    intents = []

    def intent(name: str, digest: str, size: int) -> None:
        """Assert write-ahead evidence before the no-replace link."""
        assert not destination.exists()
        intents.append((name, digest, size))

    result = saver.publish(prepared, plan, 1000, intent)
    assert destination.read_bytes() == b"complete bytes"
    assert destination.stat().st_mode & 0o777 == 0o640
    assert len(intents) == 1 and not prepared.path.exists()
    inode = destination.stat().st_ino
    assert _save(saver, source, plan) == result
    assert destination.stat().st_ino == inode
    assert len(list(config.save_root.iterdir())) == 1


def test_different_content_collision_is_before_tags_and_reuses_hash_name(tmp_path: Path) -> None:
    """Concurrent conflicts and later repeats converge on one verified copy."""
    config = _config(tmp_path)
    saver = TgSetuFileSaver(config)
    first = _source(config, "first", b"old")
    second = _source(config, "second", b"new")
    plan = naming_plan({"kind": "file", "name": "pack.tar.gz"}, "Collection", ("tag",), "fallback")
    original = _save(saver, first, plan)
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: _save(saver, second, plan), range(4)))
    assert len({result["path"] for result in results}) == 1
    stamped = Path(results[0]["path"])
    assert stamped.name.endswith("-@tag.tar.gz") and hashlib.sha256(b"new").hexdigest()[:16] in stamped.name
    inode = stamped.stat().st_ino
    assert _save(saver, second, plan, timestamp=90000) == results[0]
    assert stamped.stat().st_ino == inode
    assert Path(original["path"]).read_bytes() == b"old" and stamped.read_bytes() == b"new"
    assert len(list(config.save_root.iterdir())) == 2


def test_concurrent_distinct_bytes_same_name_preserve_both_files(tmp_path: Path) -> None:
    """Two independent transfers racing the first publication never overwrite."""
    config = _config(tmp_path)
    first = _source(config, "first", b"first")
    second = _source(config, "second", b"second")
    plan = naming_plan({"kind": "image"}, "shared", ("tag",), "fallback", 1)
    barrier = threading.Barrier(2)

    def publish(source: Path) -> Dict[str, Any]:
        """Finish both copies before racing no-replace publication."""
        saver = TgSetuFileSaver(config)
        prepared = saver.prepare(source, 100)
        barrier.wait(timeout=2)
        return saver.publish(prepared, plan, 1000, lambda name, digest, size: None)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(publish, [first, second]))
    assert len({result["path"] for result in results}) == 2
    assert [Path(result["path"]).read_bytes() for result in results] == [b"first", b"second"]
    assert all(Path(result["path"]).name.endswith("-@tag.jpg") for result in results)
    assert len(list(config.save_root.iterdir())) == 2


@pytest.mark.parametrize("kind", ["symlink", "directory"])
def test_occupied_target_never_overwritten_or_reused(tmp_path: Path, kind: str) -> None:
    """A symlink or directory is a real collision, even with matching bytes."""
    config = _config(tmp_path)
    source = _source(config, "native", b"bytes")
    config.save_root.mkdir()
    original = config.save_root / "name.jpg"
    if kind == "symlink":
        original.symlink_to(source)
    else:
        original.mkdir()
    saver = TgSetuFileSaver(config)
    result = _save(saver, source, naming_plan({"kind": "image"}, "name", (), "fallback"))
    assert Path(result["path"]) != original
    assert original.is_symlink() if kind == "symlink" else original.is_dir()


@pytest.mark.parametrize("case", ["outside", "symlink", "directory", "empty", "oversize", "cancel"])
def test_rejected_copy_leaves_no_partial_final_file(tmp_path: Path, case: str) -> None:
    """Confinement, regular-file, size and cancellation checks precede publication."""
    config = replace(_config(tmp_path), max_file_bytes=10)
    source = _source(config, "native", b"allowed")
    stop = threading.Event()
    if case == "outside":
        source = tmp_path / "private"
        source.write_bytes(b"secret")
    elif case == "symlink":
        target = tmp_path / "private"
        target.write_bytes(b"secret")
        source.unlink()
        source.symlink_to(target)
    elif case == "directory":
        source.unlink()
        source.mkdir()
    elif case == "empty":
        source.write_bytes(b"")
    elif case == "oversize":
        source.write_bytes(b"x" * 11)
    else:
        stop.set()
    with pytest.raises((TgSetuFileError, OSError)):
        TgSetuFileSaver(config).prepare(source, 10, stop)
    assert not list(config.save_root.glob("*"))
    assert not list(config.save_root.glob(".tgsetu-incoming-*"))


def test_large_local_file_is_streamed_and_reconciled(tmp_path: Path) -> None:
    """>20 MB needs bounded local reads and correct whole-content evidence."""
    config = _config(tmp_path)
    source = _source(config, "large", b"")
    content = b"a" * 65536
    hasher = hashlib.sha256()
    with source.open("wb") as stream:
        for _ in range(337):
            stream.write(content)
            hasher.update(content)
    saver = TgSetuFileSaver(config)
    tracemalloc.start()
    try:
        result = _save(saver, source, naming_plan({"kind": "video", "name": "video.mp4"}, "", (), "fallback"))
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 2 * 1024 ** 2
    assert result["size"] == 337 * 65536 and result["sha256"] == hasher.hexdigest()
    assert saver.reconcile(Path(result["path"]).name, result["sha256"], result["size"]) == result
    assert saver.reconcile(Path(result["path"]).name, "0" * 64, result["size"]) is None


def test_cancellation_after_prepare_removes_temporary_without_publication(tmp_path: Path) -> None:
    """The caller can stop between full copy and final link."""
    config = _config(tmp_path)
    source = _source(config, "native", b"bytes")
    saver = TgSetuFileSaver(config)
    prepared = saver.prepare(source, 100)
    stop = threading.Event()
    stop.set()
    with pytest.raises(TgSetuCancelled):
        saver.publish(prepared, naming_plan({"kind": "image"}, "name", (), "fallback"),
                      1000, lambda name, digest, size: None, stop=stop)
    assert not list(config.save_root.iterdir())
