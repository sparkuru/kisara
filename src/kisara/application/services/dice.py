"""Dice rolling use case."""

import random
from typing import Tuple


def roll(start: int, end: int, count: int = 1) -> Tuple[int, ...]:
    """Return independent integer rolls within the inclusive range."""

    if count < 1 or count > 30:
        raise ValueError("count must be between 1 and 30")
    if start > end:
        start, end = end, start
    return tuple(random.randint(start, end) for _ in range(count))
