"""Roll independent dice for /roll, /r, /dice, and legacy hash aliases.

/roll [sides] draws once from 1 through sides, defaulting to 100. The form
/roll <minimum> <maximum> [count] uses inclusive bounds and returns at most 30
independent draws. Command parsing and user-facing errors live in
bot/commands/roll.py; this service only chooses the numbers.
"""

import random
from typing import Tuple


def roll(start: int, end: int, count: int = 1) -> Tuple[int, ...]:
    """Return independent integer rolls within the inclusive range."""

    if count < 1 or count > 30:
        raise ValueError("count must be between 1 and 30")
    if start > end:
        start, end = end, start
    return tuple(random.randint(start, end) for _ in range(count))
