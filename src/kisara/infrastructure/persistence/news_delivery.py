"""Durable, separate records of group and private daily brief deliveries."""

import sqlite3
from pathlib import Path


class NewsDeliveryStore:
    """Track completed sends across reconnects and process restarts."""

    def __init__(self, state_dir: str) -> None:
        """Create delivery tables while preserving deployed group records."""

        directory = Path(state_dir)
        directory.mkdir(parents=True, exist_ok=True)
        self._path = directory / "news_delivery.sqlite3"
        with sqlite3.connect(str(self._path)) as database:
            database.execute(
                "CREATE TABLE IF NOT EXISTS deliveries ("
                "day TEXT NOT NULL, group_id TEXT NOT NULL, "
                "PRIMARY KEY (day, group_id))"
            )
            database.execute(
                "CREATE TABLE IF NOT EXISTS private_deliveries ("
                "day TEXT NOT NULL, user_id TEXT NOT NULL, "
                "PRIMARY KEY (day, user_id))"
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
            self._prune(database, day)

    def was_private_sent(self, day: str, user_id: str) -> bool:
        """Return whether this person already received the dated brief."""

        with sqlite3.connect(str(self._path)) as database:
            row = database.execute(
                "SELECT 1 FROM private_deliveries WHERE day = ? AND user_id = ?",
                (day, user_id),
            ).fetchone()
        return row is not None

    def mark_private_sent(self, day: str, user_id: str) -> None:
        """Record a confirmed private send and prune old completion records."""

        with sqlite3.connect(str(self._path)) as database:
            database.execute(
                "INSERT OR IGNORE INTO private_deliveries (day, user_id) VALUES (?, ?)",
                (day, user_id),
            )
            self._prune(database, day)

    @staticmethod
    def _prune(database: sqlite3.Connection, day: str) -> None:
        """Keep the last 30 days of both kinds of completion records."""

        database.execute(
            "DELETE FROM deliveries WHERE day < date(?, '-30 days')", (day,)
        )
        database.execute(
            "DELETE FROM private_deliveries WHERE day < date(?, '-30 days')", (day,)
        )
