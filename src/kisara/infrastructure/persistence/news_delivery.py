"""Durable record of daily brief deliveries by group."""

import sqlite3
from pathlib import Path


class NewsDeliveryStore:
    """Track completed group sends across reconnects and process restarts."""

    def __init__(self, state_dir: str) -> None:
        """Create the state directory and a small SQLite delivery table."""

        directory = Path(state_dir)
        directory.mkdir(parents=True, exist_ok=True)
        self._path = directory / "news_delivery.sqlite3"
        with sqlite3.connect(str(self._path)) as database:
            database.execute(
                "CREATE TABLE IF NOT EXISTS deliveries ("
                "day TEXT NOT NULL, group_id TEXT NOT NULL, "
                "PRIMARY KEY (day, group_id))"
            )

    def was_sent(self, day: str, group_id: str) -> bool:
        """Return whether this group already received the dated brief."""

        with sqlite3.connect(str(self._path)) as database:
            row = database.execute(
                "SELECT 1 FROM deliveries WHERE day = ? AND group_id = ?",
                (day, group_id),
            ).fetchone()
        return row is not None

    def mark_sent(self, day: str, group_id: str) -> None:
        """Record a successful send before another reconnect can repeat it."""

        with sqlite3.connect(str(self._path)) as database:
            database.execute(
                "INSERT OR IGNORE INTO deliveries (day, group_id) VALUES (?, ?)",
                (day, group_id),
            )
            database.execute(
                "DELETE FROM deliveries WHERE day < date(?, '-30 days')", (day,)
            )
