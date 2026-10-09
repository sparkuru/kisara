"""SQLite state for quoted private OneBot media confirmation."""

import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class SetuStore:
    """Persist bounded batch metadata across reconnects and restarts."""

    def __init__(self, state_dir: str) -> None:
        """Create the feature database in the existing persistent state volume."""
        directory = Path(state_dir)
        directory.mkdir(parents=True, exist_ok=True)
        self._path = directory / "setu.sqlite3"
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
            if database.execute("PRAGMA user_version").fetchone()[0] < 2:
                database.execute("UPDATE batches SET state = 'expired' WHERE state = 'collecting'")
                database.execute("PRAGMA user_version = 2")
            database.execute("UPDATE batches SET state = 'awaiting' WHERE state = 'saving'")
        os.chmod(self._path, 0o600)

    def _connect(self) -> sqlite3.Connection:
        """Open one short-lived connection per transaction."""
        database = sqlite3.connect(str(self._path), timeout=10)
        database.row_factory = sqlite3.Row
        return database

    def add_setu(
        self, instance_id: str, user_id: str, message_id: str,
        media: List[Dict[str, Any]], unsupported: int, now: float,
    ) -> Optional[Dict[str, Any]]:
        """Create one setu batch for one quoted source message exactly once."""
        with self._connect() as database:
            database.execute("BEGIN IMMEDIATE")
            seen = database.execute(
                "SELECT 1 FROM seen WHERE instance_id = ? AND message_id = ?",
                (instance_id, message_id),
            ).fetchone()
            if seen:
                return None
            database.execute(
                "INSERT INTO seen VALUES (?, ?, ?)", (instance_id, message_id, now)
            )
            database.execute("DELETE FROM seen WHERE seen_at < ?", (now - 604800,))
            batch_id = uuid.uuid4().hex
            database.execute(
                "INSERT INTO batches VALUES (?, ?, ?, 'collecting', ?, ?, ?, ?, '', 0, ?, ?)",
                (batch_id, instance_id, user_id, message_id, now, now, now,
                 json.dumps(media), unsupported),
            )
            row = database.execute("SELECT * FROM batches WHERE id = ?", (batch_id,)).fetchone()
        return dict(row)

    def due(self, now: float) -> List[Dict[str, Any]]:
        """Return source batches still awaiting their first prompt."""
        with self._connect() as database:
            rows = database.execute(
                "SELECT * FROM batches WHERE state = 'collecting' AND deadline <= ? "
                "ORDER BY first_at", (now,),
            ).fetchall()
        return [dict(row) for row in rows]

    def prepare_source(
        self, instance_id: str, user_id: str, source_id: str,
        media: List[Dict[str, Any]], now: float, retry_window_seconds: int,
        direct: bool,
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Claim a fresh source action without confusing deduplication with completion.

        Expired unfinished batches retain their identity and saved checkpoints.
        Only matching ordered metadata permits refreshing unresolved locations.
        """
        with self._connect() as database:
            database.execute("BEGIN IMMEDIATE")
            row = database.execute(
                "SELECT * FROM batches WHERE instance_id = ? AND user_id = ? "
                "AND first_message_id = ? ORDER BY first_at DESC LIMIT 1",
                (instance_id, user_id, source_id),
            ).fetchone()
            if row is None:
                return "missing", None
            batch = dict(row)
            state = str(batch["state"])
            previous = json.loads(batch["media_json"])
            if state == "saving":
                return "saving", batch
            if state == "saved" or (previous and all(item.get("saved_path") for item in previous)):
                return "saved", batch
            expired = state == "expired" or (state == "awaiting" and batch["expires_at"] <= now)
            if state not in {"collecting", "awaiting", "expired"}:
                return "expired", batch
            if not direct and not expired:
                return ("prompt" if state == "collecting" else "awaiting"), batch
            refreshed = _refresh_unfinished(previous, media)
            if refreshed is None:
                return "changed", batch
            next_state = "saving" if direct else "collecting"
            expires_at = now + retry_window_seconds if expired or state == "collecting" else batch["expires_at"]
            prompt_id = source_id if direct else ""
            database.execute(
                "UPDATE batches SET state = ?, expires_at = ?, deadline = ?, "
                "prompt_id = ?, media_json = ? WHERE id = ? AND state = ?",
                (next_state, expires_at, now, prompt_id, json.dumps(refreshed), batch["id"], state),
            )
            batch.update(state=next_state, expires_at=expires_at, deadline=now,
                         prompt_id=prompt_id, media_json=json.dumps(refreshed))
            return ("save" if direct else "prompt"), batch

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

    def finish(self, batch_id: str, state: str, completed_at: Optional[float] = None,
               retry_window_seconds: int = 0) -> None:
        """Finish saving and optionally renew a retry deadline that elapsed in flight."""
        retry_expires_at = (
            completed_at + retry_window_seconds
            if completed_at is not None and retry_window_seconds > 0 else None
        )
        with self._connect() as database:
            database.execute(
                "UPDATE batches SET state = ?, expires_at = CASE "
                "WHEN ? = 'awaiting' AND state = 'saving' AND expires_at <= ? "
                "AND ? IS NOT NULL THEN ? ELSE expires_at END WHERE id = ?",
                (state, state, completed_at, retry_expires_at, retry_expires_at, batch_id),
            )

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


def _refresh_unfinished(previous: List[Dict[str, Any]],
                        current: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
    """Refresh resolver fields only when the entire ordered source still matches."""
    if len(previous) != len(current):
        return None
    for old, fresh in zip(previous, current):
        if any(str(old.get(key) or "") != str(fresh.get(key) or "")
               for key in ("kind", "name", "size")):
            return None
    refreshed = [dict(item) for item in previous]
    for old, fresh in zip(refreshed, current):
        if not old.get("saved_path"):
            old["file"] = str(fresh.get("file") or "")
            old["url"] = str(fresh.get("url") or "")
    return refreshed
