"""Durable Telegram news claims; interrupted or unknown sends never auto-replay.

One adapter owns a state directory. Keys separate day, private/group kind and ID.
Connections close after short transactions, never across network calls. Records
older than 30 days are pruned relative to the scheduler's current UTC+8 day.
"""

import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Iterator, Optional


class TelegramNewsStore:
    """Keep evidence of attempted deliveries through send/checkpoint failures."""

    def __init__(self, state_dir: str) -> None:
        root = Path(state_dir)
        root.mkdir(parents=True, exist_ok=True)
        self._path = root / "telegram_news.sqlite3"
        with self._connect() as database:
            database.execute("""CREATE TABLE IF NOT EXISTS deliveries (
                day TEXT NOT NULL, kind TEXT NOT NULL, target TEXT NOT NULL,
                status TEXT NOT NULL, next_attempt REAL NOT NULL DEFAULT 0,
                message_id TEXT, PRIMARY KEY(day, kind, target))""")
            database.execute("UPDATE deliveries SET status = 'uncertain' WHERE status = 'claimed'")
        self._path.chmod(0o600)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        database = sqlite3.connect(str(self._path), timeout=10)
        try:
            with database:
                yield database
        finally:
            database.close()

    def prune(self, day: str) -> None:
        """Retain the previous 30 days, with no historical catch-up."""
        oldest = (date.fromisoformat(day) - timedelta(days=30)).isoformat()
        with self._connect() as database:
            database.execute("DELETE FROM deliveries WHERE day < ?", (oldest,))

    def claim(self, day: str, kind: str, target: str, now: float) -> bool:
        """Atomically claim new work or a due, explicitly known rejection."""
        with self._connect() as database:
            database.execute("BEGIN IMMEDIATE")
            database.execute("""INSERT OR IGNORE INTO deliveries
                (day,kind,target,status) VALUES (?,?,?,'pending')""", (day, kind, target))
            cursor = database.execute("""UPDATE deliveries SET status='claimed'
                WHERE day=? AND kind=? AND target=? AND status IN ('pending','retry')
                AND next_attempt <= ?""", (day, kind, target, now))
            return cursor.rowcount == 1

    def complete(self, day: str, kind: str, target: str, message_id: str) -> None:
        """Checkpoint only a confirmed remote receipt; preserve claim on failure."""
        self._update(day, kind, target, "confirmed", 0, message_id)

    def reject(self, day: str, kind: str, target: str, next_attempt: float,
               permanent: bool = False) -> None:
        """Record a known rejection, retryable or terminal for this day."""
        self._update(day, kind, target, "rejected" if permanent else "retry", next_attempt)

    def uncertain(self, day: str, kind: str, target: str) -> None:
        """Keep unknown send outcomes out of automatic retry."""
        self._update(day, kind, target, "uncertain", 0)

    def _update(self, day: str, kind: str, target: str, status: str,
                next_attempt: float, message_id: Optional[str] = None) -> None:
        with self._connect() as database:
            database.execute("""UPDATE deliveries SET status=?,next_attempt=?,message_id=?
                WHERE day=? AND kind=? AND target=? AND status='claimed'""",
                (status, next_attempt, message_id, day, kind, target))

    def status(self, day: str, kind: str, target: str) -> Optional[str]:
        """Read delivery evidence for diagnostics and recovery checks."""
        with self._connect() as database:
            row = database.execute("SELECT status FROM deliveries WHERE day=? AND kind=? AND target=?",
                                   (day, kind, target)).fetchone()
        return row[0] if row else None
