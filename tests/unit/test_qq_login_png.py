"""Render real PNG modules without regenerating the authentication challenge."""

import importlib.util
import io
from pathlib import Path

import pytest
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
# Synthetic QR generated once with Segno 1.6.6; no encoder is a test/runtime dependency.
PAYLOAD = "https://txz.qq.com/p?k=synthetic-login-fixture&f=1"
MATRIX = """111111100110101010111111001111111
100000100001100110101000001000001
101110101000101110011100101011101
101110101011100100110010001011101
101110101100001111001101001011101
100000101011101001110100001000001
111111101010101010101010101111111
000000001111000010011110000000000
101111100101011001111000001111100
011000001111010011010101001101101
111111101000111101000110111010110
101100001101110101100111010011110
111101111010001010000001010111011
111100010111000101100001001101011
101010100111010110000010111110110
000010001100110100000100011011100
011100110111111101001010110110001
100011010011010010011101111101101
001111110111110100101010110110100
011001001001011110011101101111111
000111101000111100110011010111000
101111010100011110000101001001001
101100100001010001101000110001010
101000011101101010000110100111101
100010100000001011000011111110000
000000001110100011010101100010101
111111100001101101001011101010110
100000101010110011101101100011110
101110101000101010011000111111001
101110101101100101110010110011111
101110101111100110101010011101000
100000100001000100001111001011100
111111101110001101010011110100010""".splitlines()


def renderer() -> object:
    """Load the exact helper source supplied to application containers."""
    spec = importlib.util.spec_from_file_location("qq_login_png", ROOT / "deploy/qq-login-png.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def png(scale: int = 5, border: int = 4, changed: bool = False) -> bytes:
    """Build an actual RGB PNG from a fixed QR fixture, with integer scaling."""
    size = len(MATRIX) + border * 2
    image = Image.new("RGB", (size, size), "white")
    for y, row in enumerate(MATRIX):
        for x, bit in enumerate(row):
            if bit == "1":
                image.putpixel((x + border, y + border), (0, 0, 0))
    if changed:
        value = 255 if MATRIX[15][15] == "1" else 0
        image.putpixel((border + 15, border + 15), (value, value, value))
    stream = io.BytesIO()
    image.resize((size * scale, size * scale), Image.Resampling.NEAREST).save(stream, format="PNG")
    return stream.getvalue()


def terminal_pixels(text: str) -> Image.Image:
    """Interpret terminal foreground/background cells independently of Pillow reduction."""
    rows = text.splitlines()
    image = Image.new("L", (len(rows[0]), len(rows) * 2), 255)
    values = {"█": (255, 255), "▀": (255, 0), "▄": (0, 255), " ": (0, 0)}
    for y, row in enumerate(rows):
        for x, cell in enumerate(row):
            upper, lower = values[cell]
            image.putpixel((x, y * 2), upper)
            image.putpixel((x, y * 2 + 1), lower)
    return image


@pytest.mark.parametrize("scale,border", [(1, 0), (2, 2), (5, 4), (8, 8)])
def test_png_modules_and_quiet_margin_survive_terminal_reduction(scale: int, border: int) -> None:
    text = renderer().render_png(png(scale, border), 80, 30, False)
    image = terminal_pixels(text)
    assert image.size == (41, 42)
    assert len({len(row) for row in text.splitlines()}) == 1
    for y, row in enumerate(MATRIX):
        assert [image.getpixel((x + 4, y + 4)) for x in range(33)] == [0 if bit == "1" else 255 for bit in row]
    assert image.crop((0, 0, 41, 4)).getextrema() == (255, 255)
    assert image.crop((0, 0, 4, 42)).getextrema() == (255, 255)


def test_ansi_renderer_forces_contrast_and_monochrome_has_no_escape_codes() -> None:
    module = renderer()
    colored = module.render_png(png(), 80, 30, True)
    assert colored.startswith("\x1b[97;40m") and colored.endswith("\x1b[0m")
    assert "\x1b" not in module.render_png(png(), 80, 30, False)


@pytest.mark.parametrize("columns,rows", [(40, 30), (80, 20)])
def test_small_terminals_are_rejected_without_distorting_modules(columns: int, rows: int) -> None:
    with pytest.raises(ValueError, match="terminal-too-small"):
        renderer().render_png(png(), columns, rows, False)


@pytest.mark.parametrize("data", [b"", b"not-png", b"\x89PNG\r\n\x1a\n", b"x" * (1024 * 1024 + 1)],
                         ids=["empty", "not-png", "truncated", "oversized"])
def test_invalid_or_excessive_png_is_rejected(data: bytes) -> None:
    with pytest.raises(ValueError):
        renderer().render_png(data, 80, 30, False)


def test_non_qr_geometry_is_rejected() -> None:
    stream = io.BytesIO()
    Image.new("RGB", (120, 80), "black").save(stream, format="PNG")
    with pytest.raises(ValueError, match="png-geometry"):
        renderer().render_png(stream.getvalue(), 80, 30, False)
