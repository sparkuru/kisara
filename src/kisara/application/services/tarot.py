"""Daily tarot readings backed by a packaged card and spread catalog."""

import hashlib
import json
import pkgutil
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple


def _local_day() -> date:
    """Use the bot's documented China Standard Time day boundary."""

    return datetime.now(timezone(timedelta(hours=8))).date()


class TarotReader:
    """Draw a stable reading for each user and calendar day."""

    def __init__(
        self, spread_rate: int = 5, today: Callable[[], date] = _local_day,
        image_dir: Optional[str] = None,
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
        self._card_keys = {
            (card["type"], card["name_cn"]) for card in self._cards
        }
        self._formations: Tuple[Tuple[str, Mapping[str, Any]], ...] = tuple(
            formations.items()
        )
        self._spread_rate = spread_rate
        self._today = today
        self._images = self._load_images(Path(image_dir)) if image_dir else {}

    def reading(
        self, sender_id: str, instance_id: str, mode: str = "auto",
        spread_rate: int = -1,
    ) -> str:
        """Return one card or a spread, stable across restarts for the day."""

        return self.reading_with_images(sender_id, instance_id, mode, spread_rate)[0]

    def reading_with_images(
        self, sender_id: str, instance_id: str, mode: str = "auto",
        spread_rate: int = -1,
    ) -> Tuple[str, Tuple[str, ...]]:
        """Return a stable reading and local image URIs when art is installed."""

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
            reading = "Tarot for {}:\n{}".format(day, self._format_card(card, rng))
            return reading, self._image_uris((card,), digest)

        formation_name, formation = rng.choice(self._formations)
        count = formation["cards_num"]
        positions = rng.choice(formation["representations"])
        if formation.get("is_cut") and len(positions) > count:
            positions = positions[: count - 1] + [positions[-1]]
        drawn = rng.sample(self._cards, count)
        lines: List[str] = ["Tarot for {} — {}:".format(day, formation_name)]
        for position, card in zip(positions, drawn):
            lines.append("{}: {}".format(position, self._format_card(card, rng)))
        return "\n".join(lines), self._image_uris(tuple(drawn), digest)

    def _load_images(
        self, image_dir: Path
    ) -> Dict[Tuple[str, str], Tuple[Path, ...]]:
        """Match packaged image names to installed art without changing meanings."""

        if not image_dir.is_dir():
            return {}
        content = pkgutil.get_data("kisara.resources", "tarot_images.json")
        if content is None:
            raise FileNotFoundError("Packaged tarot image index is unavailable.")
        cards = json.loads(content.decode("utf-8"))
        if not isinstance(cards, list) or len(cards) != 78:
            raise ValueError("Packaged tarot image index must contain 78 cards.")

        images: Dict[Tuple[str, str], Tuple[Path, ...]] = {}
        for card in cards:
            if not isinstance(card, dict):
                raise ValueError("Packaged tarot image index has an invalid card.")
            card_type = card.get("type")
            name = card.get("name_cn")
            picture_names = card.get("pic")
            if not isinstance(card_type, str) or not isinstance(name, str):
                raise ValueError("Packaged tarot image index has an invalid card identity.")
            if not isinstance(picture_names, list):
                raise ValueError("Packaged tarot image index has invalid picture names.")
            if (card_type, name) not in self._card_keys:
                raise ValueError("Packaged tarot image index does not match the deck.")
            folder = image_dir / card_type
            available = []
            for picture_name in picture_names:
                if (not isinstance(picture_name, str)
                        or Path(picture_name).name != picture_name
                        or picture_name in {"", ".", ".."}):
                    raise ValueError("Packaged tarot image index contains an invalid path.")
                picture = folder / (picture_name + ".png")
                if picture.is_file() and picture.resolve().parent == folder.resolve():
                    available.append(picture.resolve())
            images[(card_type, name)] = tuple(dict.fromkeys(available))
        return images

    def _image_uris(
        self, cards: Tuple[Mapping[str, Any], ...], digest: bytes
    ) -> Tuple[str, ...]:
        """Choose installed variants without consuming the reading's random stream."""

        uris = []
        for index, card in enumerate(cards):
            options = self._images.get((card["type"], card["name_cn"]), ())
            if not options:
                continue
            selector = hashlib.sha256(
                digest + bytes([index]) + card["name_en"].encode("utf-8")
            )
            chosen = int.from_bytes(selector.digest(), "big") % len(options)
            uris.append(options[chosen].as_uri())
        return tuple(uris)

    @staticmethod
    def _format_card(card: Mapping[str, Any], rng: random.Random) -> str:
        """Render one card with a deterministic orientation and meaning."""

        upright = bool(rng.getrandbits(1))
        orientation = "upright" if upright else "reversed"
        meaning = card["meaning"]["up" if upright else "down"]
        return "{} / {} ({}): {}".format(
            card["name_cn"], card["name_en"], orientation, meaning
        )
