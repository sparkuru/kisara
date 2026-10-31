"""Render an existing login PNG through the application's Pillow runtime.

Internal helper: PNG bytes arrive on stdin, never as a URL or command argument.
The first output line is a private digest for duplicate suppression.
"""

import hashlib
import io
import sys
from typing import List

from PIL import Image, UnidentifiedImageError


MAX_PNG_BYTES = 1024 * 1024
MAX_PNG_EDGE = 2048


def qr_modules(data: bytes) -> List[List[bool]]:
    """Reduce whole QR modules, retaining the bitmap's existing information."""
    if not data or len(data) > MAX_PNG_BYTES:
        raise ValueError("png-size")
    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.format != "PNG" or max(source.size) > MAX_PNG_EDGE:
                raise ValueError("png-size")
            background = Image.new("RGBA", source.size, "white")
            image = Image.alpha_composite(background, source.convert("RGBA")).convert("L")
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as error:
        raise ValueError("png-invalid") from error
    dark = image.point(lambda value: 255 if value < 128 else 0)
    bounds = dark.getbbox()
    if bounds is None:
        raise ValueError("png-geometry")
    left, top, right, bottom = bounds
    run = 0
    while left + run < right and dark.getpixel((left + run, top)):
        run += 1
    pitch = run // 7
    width = right - left
    if not pitch or run % 7 or width != bottom - top or width % pitch:
        raise ValueError("png-geometry")
    size = width // pitch
    if not 21 <= size <= 177 or (size - 21) % 4:
        raise ValueError("png-geometry")
    modules = []
    for y in range(size):
        row = []
        for x in range(size):
            cell = dark.crop((left + x * pitch, top + y * pitch,
                              left + (x + 1) * pitch, top + (y + 1) * pitch))
            minimum, maximum = cell.getextrema()
            if minimum != maximum:
                raise ValueError("png-geometry")
            row.append(bool(maximum))
        modules.append(row)
    return modules


def render_png(data: bytes, columns: int, rows: int, color: bool) -> str:
    """Serialize monochrome half-block cells with a four-module quiet margin."""
    modules = qr_modules(data)
    size = len(modules) + 8
    if columns < size or rows < (size + 1) // 2:
        raise ValueError("terminal-too-small")
    light = [False] * size
    matrix = [light] * 4 + [[False] * 4 + row + [False] * 4 for row in modules] + [light] * 5
    cells = {(False, False): "█", (False, True): "▀", (True, False): "▄", (True, True): " "}
    output = ["".join(cells[(upper, lower)] for upper, lower in zip(matrix[y], matrix[y + 1]))
              for y in range(0, size, 2)]
    text = "\n".join(output)
    return "\x1b[97;40m" + text + "\x1b[0m" if color else text


def main() -> int:
    """Return only controlled error categories; never print input PNG content."""
    try:
        if len(sys.argv) != 4:
            return 2
        data = sys.stdin.buffer.read(MAX_PNG_BYTES + 1)
        text = render_png(data, int(sys.argv[1]), int(sys.argv[2]), sys.argv[3] == "color")
    except (ValueError, OSError) as error:
        category = str(error) if str(error) in {"png-size", "png-invalid", "png-geometry", "terminal-too-small"} else "png-invalid"
        sys.stderr.write(category + "\n")
        return 1
    sys.stdout.write(hashlib.sha256(data).hexdigest() + "\n" + text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
