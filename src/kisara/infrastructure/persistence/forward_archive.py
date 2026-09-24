"""SQLite state for private forward collection and confirmation."""

import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class ForwardArchiveStore:
    """Persist bounded batch metadata across reconnects and restarts."""

    def __init__(self, state_dir: str) -> None:
        """Create the feature database in the existing persistent state volume."""
        directory = Path(state_dir)
        directory.mkdir(parents=True, exist_ok=True)
        self._path = directory / "forward_archive.sqlite3"
        with self._connect() as database:
            database.execute(
                "CREATE TABLE IF NOT EXISTS batches ("
                "id TEXT PRIMARY KEY, instance_id TEXT NOT NULL, user_id TEXT NOT NULL, "
                "state TEXT NOT NULL, first_message_id TEXT NOT NULL, first_at REAL NOT NULL, "
                "last_at REAL NOT NULL, deadline REAL NOT NULL, prompt_id TEXT NOT NULL, "
                "expires_at REAL NOT NULL, media_json TEXT NOT NULL, unsupported INTEGER NOT NULL)"
            )
            database.execute(
                "CREATE INDEX IF NOT EXISTS batches_status ON batches(state, deadline)"
            )
            database.execute(
                "CREATE TABLE IF NOT EXISTS seen (instance_id TEXT NOT NULL, "
                "message_id TEXT NOT NULL, seen_at REAL NOT NULL, "
                "PRIMARY KEY(instance_id, message_id))"
            )
            database.execute("UPDATE batches SET state = 'awaiting' WHERE state = 'saving'")
        os.chmod(self._path, 0o600)

    def _connect(self) -> sqlite3.Connection:
        """Open one short-lived connection per transaction."""
        database = sqlite3.connect(str(self._path), timeout=10)
        database.row_factory = sqlite3.Row
        return database

    def add_message(
        self, instance_id: str, user_id: str, message_id: str,
        media: List[Dict[str, Any]], unsupported: int, now: float,
        quiet_seconds: int, max_seconds: int, max_nodes: int,
    ) -> bool:
        """Add an event exactly once to the current fixed-window batch."""
        with self._connect() as database:
            database.execute("BEGIN IMMEDIATE")
            seen = database.execute(
                "SELECT 1 FROM seen WHERE instance_id = ? AND message_id = ?",
                (instance_id, message_id),
            ).fetchone()
            if seen:
                return False
            database.execute(
                "INSERT INTO seen VALUES (?, ?, ?)", (instance_id, message_id, now)
            )
            database.execute("DELETE FROM seen WHERE seen_at < ?", (now - 604800,))
            row = database.execute(
                "SELECT * FROM batches WHERE instance_id = ? AND user_id = ? "
                "AND state = 'collecting' AND deadline > ? ORDER BY first_at DESC LIMIT 1",
                (instance_id, user_id, now),
            ).fetchone()
            if row is None:
                if len(media) > max_nodes:
                    unsupported += len(media) - max_nodes
                    media = media[:max_nodes]
                database.execute(
                    "INSERT INTO batches VALUES (?, ?, ?, 'collecting', ?, ?, ?, ?, '', 0, ?, ?)",
                    (uuid.uuid4().hex, instance_id, user_id, message_id, now, now,
                     now + min(quiet_seconds, max_seconds), json.dumps(media), unsupported),
                )
            else:
                items = json.loads(row["media_json"])
                available = max(0, max_nodes - len(items))
                if len(media) > available:
                    unsupported += len(media) - available
                    media = media[:available]
                items.extend(media)
                deadline = min(row["first_at"] + max_seconds, now + quiet_seconds)
                database.execute(
                    "UPDATE batches SET last_at = ?, deadline = ?, media_json = ?, "
                    "unsupported = unsupported + ? WHERE id = ?",
                    (now, deadline, json.dumps(items), unsupported, row["id"]),
                )
        return True

    def due(self, now: float) -> List[Dict[str, Any]]:
        """Return batches whose silence or fixed deadline has elapsed."""
        with self._connect() as database:
            rows = database.execute(
                "SELECT * FROM batches WHERE state = 'collecting' AND deadline <= ? "
                "ORDER BY first_at", (now,),
            ).fetchall()
        return [dict(row) for row in rows]

    def awaiting(self, instance_id: str, user_id: str, now: float) -> List[Dict[str, Any]]:
        """Find unexpired confirmations for one sender."""
        with self._connect() as database:
            rows = database.execute(
                "SELECT * FROM batches WHERE instance_id = ? AND user_id = ? "
                "AND state = 'awaiting' AND expires_at > ? ORDER BY first_at",
                (instance_id, user_id, now),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_awaiting(self, batch_id: str, expires_at: float) -> bool:
        """Claim a prompt once before performing the external send."""
        with self._connect() as database:
            cursor = database.execute(
                "UPDATE batches SET state = 'awaiting', expires_at = ? "
                "WHERE id = ? AND state = 'collecting'",
                (expires_at, batch_id),
            )
        return cursor.rowcount == 1

    def unprompted(self, now: float) -> List[Dict[str, Any]]:
        """Return confirmations whose prompt send needs another attempt."""
        with self._connect() as database:
            rows = database.execute(
                "SELECT * FROM batches WHERE state = 'awaiting' AND prompt_id = '' "
                "AND deadline <= ? AND expires_at > ? ORDER BY first_at",
                (now, now),
            ).fetchall()
        return [dict(row) for row in rows]

    def retry_prompt_after(self, batch_id: str, deadline: float) -> None:
        """Avoid a tight retry loop when the platform cannot send a prompt."""
        with self._connect() as database:
            database.execute(
                "UPDATE batches SET deadline = ? WHERE id = ? AND state = 'awaiting'",
                (deadline, batch_id),
            )

    def set_prompt(self, batch_id: str, prompt_id: str) -> None:
        """Record the bot message used to disambiguate quoted confirmations."""
        with self._connect() as database:
            database.execute("UPDATE batches SET prompt_id = ? WHERE id = ?", (prompt_id, batch_id))

    def claim_save(self, batch_id: str, now: float) -> bool:
        """Prevent concurrent or repeated confirmation from starting two saves."""
        with self._connect() as database:
            cursor = database.execute(
                "UPDATE batches SET state = 'saving' WHERE id = ? "
                "AND state = 'awaiting' AND expires_at > ?", (batch_id, now),
            )
        return cursor.rowcount == 1

    def update_media(self, batch_id: str, media: List[Dict[str, Any]]) -> None:
        """Checkpoint each completed file before processing the next one."""
        with self._connect() as database:
            database.execute("UPDATE batches SET media_json = ? WHERE id = ?",
                             (json.dumps(media), batch_id))

    def finish(self, batch_id: str, state: str) -> None:
        """Set a terminal or retryable batch state."""
        with self._connect() as database:
            database.execute("UPDATE batches SET state = ? WHERE id = ?", (state, batch_id))

    def expire(self, now: float) -> None:
        """Remove expired confirmations and old terminal metadata."""
        with self._connect() as database:
            database.execute(
                "UPDATE batches SET state = 'expired' WHERE state = 'awaiting' AND expires_at <= ?",
                (now,),
            )
            database.execute(
                "DELETE FROM batches WHERE state IN ('saved', 'cancelled', 'expired') "
                "AND first_at < ?", (now - 604800,),
            )

    def recover_saving(self) -> None:
        """Allow unfinished saves to retry after a lost connection."""
        with self._connect() as database:
            database.execute("UPDATE batches SET state = 'awaiting' WHERE state = 'saving'")
