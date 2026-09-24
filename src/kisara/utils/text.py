"""Renderer-independent text wrapping helpers."""

from typing import Callable, Tuple


def wrap_text(text: str, max_width: float,
              text_width: Callable[[str], float]) -> Tuple[str, ...]:
    """Wrap text at character boundaries using the caller's width function."""

    if max_width <= 0:
        raise ValueError("max_width must be positive")
    lines = []
    current = ""
    for character in text:
        candidate = current + character
        if current and text_width(candidate) > max_width:
            lines.append(current)
            current = character
        else:
            current = candidate
    if current:
        lines.append(current)
    return tuple(lines)
