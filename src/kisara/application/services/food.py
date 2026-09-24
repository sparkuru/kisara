"""Choose five distinct /eat suggestions from packaged legacy food data.

The source list is kisara.resources/foods.json, included in the Python package.
/eat and legacy Chinese food phrases are routed by bot/dispatcher.py; this
service samples the list and bot/commands/eat.py formats the reply. No database
or user-specific state is kept.
"""

import json
import pkgutil
import random
from typing import Tuple


def recommend_foods(count: int = 5) -> Tuple[str, ...]:
    """Choose up to ``count`` distinct food suggestions."""

    if count < 1:
        raise ValueError("count must be positive")

    content = pkgutil.get_data("kisara.resources", "foods.json")
    if content is None:
        raise FileNotFoundError("Packaged food data is unavailable.")
    foods = json.loads(content.decode("utf-8"))
    if (
        not isinstance(foods, list)
        or not foods
        or any(not isinstance(food, str) or not food.strip() for food in foods)
    ):
        raise ValueError("packaged food data must be a non-empty string list")

    options = tuple(dict.fromkeys(foods))
    return tuple(random.sample(options, min(count, len(options))))
