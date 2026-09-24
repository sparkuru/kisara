"""Verify reusable spacing, wrapping, and atomic file helpers."""

from pathlib import Path

from kisara.utils.files import atomic_write_bytes
from kisara.utils.pangu import pangu
from kisara.utils.text import wrap_text


def test_pangu_spaces_mixed_plain_text_without_changing_paragraphs() -> None:
    """CJK, Latin text, numbers, and brackets should receive stable spacing."""

    source = "「60秒读懂世界」AI技术增长5%。\n\n中文(English)测试"
    expected = "「60 秒读懂世界」AI 技术增长 5%。\n\n中文 (English) 测试"

    assert pangu(source) == expected
    assert pangu(expected) == expected


def test_pangu_preserves_url_paths_and_plain_ascii() -> None:
    """Formatting a sentence should not insert spaces into a URL."""

    assert pangu("详见https://example.com/中文路径") == "详见 https://example.com/中文路径"
    assert pangu("Only ASCII 123") == "Only ASCII 123"


def test_wrap_text_uses_caller_measurement() -> None:
    """The helper should work without depending on a particular renderer."""

    assert wrap_text("中文ABC", 3, lambda value: float(len(value))) == ("中文A", "BC")


def test_atomic_write_bytes_replaces_complete_file(tmp_path: Path) -> None:
    """A later write should replace the file and leave no temporary artifact."""

    path = tmp_path / "sample.bin"
    atomic_write_bytes(path, b"first")
    atomic_write_bytes(path, b"second")

    assert path.read_bytes() == b"second"
    assert list(tmp_path.iterdir()) == [path]
