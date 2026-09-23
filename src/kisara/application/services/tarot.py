"""Daily tarot readings backed by a packaged card and spread catalog."""

import hashlib
import json
import pkgutil
import random
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, List, Mapping, Tuple


def _local_day() -> date:
    """Use the bot's documented China Standard Time day boundary."""

    return datetime.now(timezone(timedelta(hours=8))).date()


class TarotReader:
    """Draw a stable reading for each user and calendar day."""

    def __init__(
        self, spread_rate: int = 5, today: Callable[[], date] = _local_day
    ) -> None:
        """Load the packaged deck and validate its basic structure."""

        if spread_rate < 0 or spread_rate > 100:
            raise ValueError("spread_rate must be between 0 and 100")
        content = pkgutil.get_data("kisara.resources", "tarot.json")
        if content is None:
            raise FileNotFoundError("Packaged tarot data is unavailable.")
        catalog = json.loads(content.decode("utf-8"))
        cards = catalog.get("cards")
        formations = catalog.get("formations")
        if not isinstance(cards, dict) or len(cards) != 78:
            raise ValueError("Packaged tarot data must contain 78 cards.")
        if not isinstance(formations, dict) or not formations:
            raise ValueError("Packaged tarot data has no spreads.")

        self._cards: Tuple[Mapping[str, Any], ...] = tuple(cards.values())
        self._formations: Tuple[Tuple[str, Mapping[str, Any]], ...] = tuple(
            formations.items()
        )
        self._spread_rate = spread_rate
        self._today = today

    def reading(
        self, sender_id: str, instance_id: str, mode: str = "auto",
        spread_rate: int = -1,
    ) -> str:
        """Return one card or a spread, stable across restarts for the day."""

        if mode not in {"auto", "single", "spread"}:
            raise ValueError("mode must be auto, single, or spread")
        if spread_rate == -1:
            spread_rate = self._spread_rate
        if spread_rate < 0 or spread_rate > 100:
            raise ValueError("spread_rate must be between 0 and 100")
        day = self._today()
        seed = "{}\0{}\0{}".format(instance_id, sender_id, day.isoformat())
        digest = hashlib.sha256(seed.encode("utf-8")).digest()
        rng = random.Random(int.from_bytes(digest, "big"))
        if mode == "auto":
            selector = hashlib.sha256(digest + b"spread-selector").digest()
            choice = int.from_bytes(selector, "big") % 100 + 1
            mode = "spread" if choice <= spread_rate else "single"

        if mode == "single":
            card = rng.choice(self._cards)
            return "Tarot for {}:\n{}".format(day, self._format_card(card, rng))

        formation_name, formation = rng.choice(self._formations)
        count = formation["cards_num"]
        positions = rng.choice(formation["representations"])
        if formation.get("is_cut") and len(positions) > count:
            positions = positions[: count - 1] + [positions[-1]]
        drawn = rng.sample(self._cards, count)
        lines: List[str] = ["Tarot for {} — {}:".format(day, formation_name)]
        for position, card in zip(positions, drawn):
            lines.append("{}: {}".format(position, self._format_card(card, rng)))
        return "\n".join(lines)

    @staticmethod
    def _format_card(card: Mapping[str, Any], rng: random.Random) -> str:
        """Render one card with a deterministic orientation and meaning."""

        upright = bool(rng.getrandbits(1))
        orientation = "upright" if upright else "reversed"
        meaning = card["meaning"]["up" if upright else "down"]
        return "{} / {} ({}): {}".format(
            card["name_cn"], card["name_en"], orientation, meaning
        )
