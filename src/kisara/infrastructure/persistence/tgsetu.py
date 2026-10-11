"""Private SQLite activation, per-file claims and publication recovery evidence.

One runtime owns this state directory. Transactions cover metadata only, never
SDK retrieval or file copying. Successful archive bytes are never pruned; old
terminal metadata is retained for seven days. Interrupted worker claims become
queued on startup with their frozen name and prepared publication intent intact.
"""

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional, Sequence

from kisara.config.tgsetu import TgSetuConfig
from kisara.infrastructure.persistence.tgsetu_files import naming_plan


class TgSetuQueueError(ValueError):
    """An incoming logical unit exceeds the configured acceptance budget."""


class TgSetuStore:
    """Persist independently retryable files, scoped by instance/chat/user."""

    def __init__(self, state_dir: str) -> None:
        """Create the feature-local schema with private database permissions."""
        root = Path(state_dir)
        root.mkdir(parents=True, exist_ok=True)
        self._path = root / "tgsetu.sqlite3"
        descriptor = os.open(str(self._path), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.fchmod(descriptor, 0o600)
        os.close(descriptor)
        with self._connect() as database:
            database.executescript("""
                CREATE TABLE IF NOT EXISTS activation (
                    instance TEXT NOT NULL, chat TEXT NOT NULL, user TEXT NOT NULL,
                    active INTEGER NOT NULL, PRIMARY KEY(instance, chat, user));
                CREATE TABLE IF NOT EXISTS units (
                    id TEXT PRIMARY KEY, instance TEXT NOT NULL, chat TEXT NOT NULL,
                    user TEXT NOT NULL, album TEXT NOT NULL, first_at REAL NOT NULL,
                    last_at REAL NOT NULL, frozen INTEGER NOT NULL DEFAULT 0,
                    title TEXT NOT NULL DEFAULT '', tags_json TEXT NOT NULL DEFAULT '[]',
                    fallback TEXT NOT NULL DEFAULT '', captionless INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS members (
                    id INTEGER PRIMARY KEY, unit_id TEXT NOT NULL REFERENCES units(id),
                    message_id TEXT NOT NULL, item_index INTEGER NOT NULL,
                    media_json TEXT NOT NULL, declared_size INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued', ordinal INTEGER NOT NULL DEFAULT 0,
                    plan_json TEXT NOT NULL DEFAULT '', candidate TEXT NOT NULL DEFAULT '',
                    sha256 TEXT NOT NULL DEFAULT '', size INTEGER NOT NULL DEFAULT 0,
                    saved_path TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT '',
                    updated_at REAL NOT NULL,
                    UNIQUE(unit_id, message_id, item_index));
                CREATE INDEX IF NOT EXISTS tgsetu_status ON members(status, unit_id);
                PRAGMA user_version = 1;
            """)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Close every short-lived connection, including rolled-back failures."""
        database = sqlite3.connect(str(self._path), timeout=10)
        database.row_factory = sqlite3.Row
        database.execute("PRAGMA foreign_keys = ON")
        try:
            with database:
                yield database
        finally:
            database.close()

    def is_active(self, instance: str, chat: str, user: str) -> bool:
        """Return durable opt-in without interpreting unrelated users' state."""
        with self._connect() as database:
            row = database.execute(
                "SELECT active FROM activation WHERE instance=? AND chat=? AND user=?",
                (instance, chat, user),
            ).fetchone()
        return row is not None and bool(row["active"])

    def set_active(self, instance: str, chat: str, user: str, active: bool) -> None:
        """Change only future acceptance; existing members retain their state."""
        with self._connect() as database:
            database.execute("INSERT OR REPLACE INTO activation VALUES(?,?,?,?)",
                             (instance, chat, user, int(active)))

    def enqueue(self, instance: str, chat: str, user: str, message_id: str,
                media: Sequence[Mapping[str, Any]], now: float, config: TgSetuConfig) -> Dict[str, Any]:
        """Atomically deduplicate and accept one actual message within caps."""
        album = str(media[0].get("media_group_id") or "")
        identity = json.dumps([instance, chat, user, "album" if album else "message",
                               album or message_id], ensure_ascii=False)
        unit_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        with self._connect() as database:
            database.execute("BEGIN IMMEDIATE")
            unit = database.execute("SELECT * FROM units WHERE id=?", (unit_id,)).fetchone()
            known = {row["item_index"] for row in database.execute(
                "SELECT item_index FROM members JOIN units ON units.id=members.unit_id "
                "WHERE units.instance=? AND units.chat=? AND members.message_id=?",
                (instance, chat, message_id))}
            new = [(index, item) for index, item in enumerate(media) if index not in known]
            if not new:
                return {"unit_id": unit_id, "accepted": 0}
            pending = database.execute(
                "SELECT COUNT(*) FROM members WHERE status IN ('queued','working')"
            ).fetchone()[0]
            if pending + len(new) > config.max_pending_files:
                raise TgSetuQueueError("Archive queue is full; resend after pending files finish.")
            existing = list(database.execute("SELECT * FROM members WHERE unit_id=?", (unit_id,)))
            if len(existing) + len(new) > config.max_unit_files:
                raise TgSetuQueueError("Logical message file limit reached.")
            sizes = [int(item.get("size") or 0) for _, item in new]
            if any(size < 0 or size > config.max_file_bytes for size in sizes):
                raise TgSetuQueueError("Media exceeds the configured file size limit.")
            total = sum(row["size"] if row["status"] == "saved" else row["declared_size"]
                        for row in existing) + sum(sizes)
            if total > config.max_unit_bytes:
                raise TgSetuQueueError("Logical message byte limit reached.")
            if unit is None:
                database.execute(
                    "INSERT INTO units(id,instance,chat,user,album,first_at,last_at) VALUES(?,?,?,?,?,?,?)",
                    (unit_id, instance, chat, user, album, now, now))
            else:
                database.execute("UPDATE units SET last_at=? WHERE id=?", (now, unit_id))
            for (index, item), size in zip(new, sizes):
                database.execute(
                    "INSERT INTO members(unit_id,message_id,item_index,media_json,declared_size,updated_at) "
                    "VALUES(?,?,?,?,?,?)", (unit_id, message_id, index,
                                          json.dumps(dict(item), ensure_ascii=False), size, now))
            if unit is not None and unit["frozen"]:
                self._name_new(database, dict(unit), config)
            return {"unit_id": unit_id, "accepted": len(new)}

    def _name_new(self, database: sqlite3.Connection, unit: Mapping[str, Any],
                  config: TgSetuConfig) -> None:
        """Freeze initial ordinals or append late ordinals without renumbering."""
        members = list(database.execute("SELECT * FROM members WHERE unit_id=?", (unit["id"],)))
        members.sort(key=lambda row: (int(row["message_id"]), row["item_index"]))
        next_ordinal = max((row["ordinal"] for row in members), default=0) + 1
        used_names = {json.loads(row["plan_json"])["name"] for row in members if row["plan_json"]}
        for row in members:
            if row["plan_json"] or row["status"] == "failed":
                continue
            media = json.loads(row["media_json"])
            ordinal = next_ordinal if unit["album"] else 0
            next_ordinal += 1
            use_ordinal = ordinal if unit["album"] and media["kind"] != "file" else 0
            try:
                title = unit["title"] or (unit["fallback"] if unit["album"] and media["kind"] != "file" else "")
                plan = naming_plan(media, title, tuple(json.loads(unit["tags_json"])),
                                   unit["fallback"], use_ordinal)
                if plan["name"] in used_names:
                    plan = naming_plan(media, title, tuple(json.loads(unit["tags_json"])),
                                       unit["fallback"], ordinal)
                used_names.add(plan["name"])
                database.execute("UPDATE members SET ordinal=?,plan_json=? WHERE id=?",
                                 (ordinal, json.dumps(plan, ensure_ascii=False), row["id"]))
            except ValueError:
                database.execute("UPDATE members SET ordinal=?,status='failed',error='NamingError' WHERE id=?",
                                 (ordinal, row["id"]))

    def freeze_due(self, instance: str, now: float, config: TgSetuConfig,
                   authorized: Callable[[str], bool]) -> None:
        """Choose initial captions after quiet/max wait, without closing albums."""
        with self._connect() as database:
            database.execute("BEGIN IMMEDIATE")
            units = list(database.execute("SELECT * FROM units WHERE frozen=0 AND instance=?", (instance,)))
            for row in units:
                if not authorized(row["user"]):
                    continue
                if row["album"] and now < min(row["last_at"] + config.album_quiet_seconds,
                                             row["first_at"] + config.album_max_wait_seconds):
                    continue
                members = list(database.execute("SELECT * FROM members WHERE unit_id=?", (row["id"],)))
                members.sort(key=lambda item: (int(item["message_id"]), item["item_index"]))
                media = [json.loads(item["media_json"]) for item in members]
                selected = next((item for item in media if item.get("caption")), media[0])
                fallback = "tg-{}-{}".format(row["chat"], row["id"][:12] if row["album"]
                                              else members[0]["message_id"])
                unit = dict(row)
                unit.update(title=str(selected.get("title") or ""),
                            tags_json=json.dumps(selected.get("tags") or [], ensure_ascii=False),
                            fallback=fallback, captionless=int(not selected.get("caption")))
                database.execute("UPDATE units SET frozen=1,title=?,tags_json=?,fallback=?,captionless=? WHERE id=?",
                                 (unit["title"], unit["tags_json"], fallback, unit["captionless"], row["id"]))
                self._name_new(database, unit, config)

    def claim(self, instance: str, authorized: Callable[[str], bool]) -> Optional[Dict[str, Any]]:
        """Claim one file, serializing a unit's byte budget across workers."""
        with self._connect() as database:
            database.execute("BEGIN IMMEDIATE")
            rows = database.execute(
                "SELECT members.*,units.instance,units.chat,units.user,units.first_at,units.album,units.captionless "
                "FROM members JOIN units ON units.id=members.unit_id WHERE members.status='queued' AND units.instance=? "
                "AND units.frozen=1 AND members.plan_json!='' "
                "AND NOT EXISTS(SELECT 1 FROM members busy WHERE busy.unit_id=units.id AND busy.status='working') "
                "ORDER BY units.first_at,members.ordinal,members.id", (instance,))
            selected = next((dict(row) for row in rows if authorized(row["user"])), None)
            if selected is None:
                return None
            database.execute("UPDATE members SET status='working' WHERE id=? AND status='queued'",
                             (selected["id"],))
            selected["used_bytes"] = database.execute(
                "SELECT COALESCE(SUM(size),0) FROM members WHERE unit_id=? AND status='saved'",
                (selected["unit_id"],)).fetchone()[0]
            return selected

    def naming_failures(self, instance: str, authorized: Callable[[str], bool]) -> List[Dict[str, Any]]:
        """Surface failed naming plans which cannot reach the transfer workers."""
        with self._connect() as database:
            database.execute("BEGIN IMMEDIATE")
            rows = database.execute(
                "SELECT members.*,units.instance,units.chat,units.user,units.first_at,units.album,units.captionless "
                "FROM members JOIN units ON units.id=members.unit_id WHERE units.instance=? "
                "AND members.status='failed' AND members.error='NamingError'", (instance,))
            failed = [dict(row) for row in rows if authorized(row["user"])]
            for row in failed:
                database.execute("UPDATE members SET error='NamingErrorReported' WHERE id=?", (row["id"],))
            return failed

    def intent(self, member_id: int, candidate: str, digest: str, size: int) -> None:
        """Record selected complete bytes before any no-replace publication."""
        with self._connect() as database:
            changed = database.execute("UPDATE members SET candidate=?,sha256=?,size=? WHERE id=? AND status='working'",
                                       (candidate, digest, size, member_id)).rowcount
            if changed != 1:
                raise RuntimeError("Archive claim no longer belongs to this worker.")

    def complete(self, member_id: int, result: Mapping[str, Any], now: float) -> None:
        """Checkpoint success only after synced publication or reconciliation."""
        with self._connect() as database:
            database.execute("UPDATE members SET status='saved',saved_path=?,sha256=?,size=?,error='',updated_at=? "
                             "WHERE id=? AND status='working'",
                             (str(result["path"]), result["sha256"], result["size"], now, member_id))

    def fail(self, member_id: int, category: str, now: float, queued: bool = False) -> None:
        """Preserve planned names and intents when a worker fails or stops."""
        with self._connect() as database:
            database.execute("UPDATE members SET status=?,error=?,updated_at=? WHERE id=? AND status='working'",
                             ("queued" if queued else "failed", category, now, member_id))

    def retry(self, instance: str, chat: str, user: str, source_id: str,
              config: TgSetuConfig, now: float) -> int:
        """Requeue only failed members of the owned source logical unit."""
        with self._connect() as database:
            database.execute("BEGIN IMMEDIATE")
            units = list(database.execute(
                "SELECT DISTINCT units.* FROM units JOIN members ON members.unit_id=units.id "
                "WHERE instance=? AND chat=? AND user=? AND message_id=?",
                (instance, chat, user, source_id)))
            if len(units) != 1:
                return 0
            unit = units[0]
            count = database.execute("SELECT COUNT(*) FROM members WHERE unit_id=? AND status='failed' AND plan_json!=''",
                                     (unit["id"],)).fetchone()[0]
            pending = database.execute("SELECT COUNT(*) FROM members WHERE status IN ('queued','working')").fetchone()[0]
            if pending + count > config.max_pending_files:
                raise TgSetuQueueError("Archive queue is full; retry after pending files finish.")
            database.execute("UPDATE members SET status='queued',error='',updated_at=? "
                             "WHERE unit_id=? AND status='failed' AND plan_json!=''", (now, unit["id"]))
            return count

    def recover(self) -> None:
        """Reopen interrupted claims without changing success or failure state."""
        with self._connect() as database:
            database.execute("UPDATE members SET status='queued' WHERE status='working'")

    def summary(self, unit_id: str) -> Dict[str, Any]:
        """Count received sources and current file outcomes, never selections."""
        with self._connect() as database:
            members = [dict(row) for row in database.execute("SELECT * FROM members WHERE unit_id=?", (unit_id,))]
        return {"messages": len({row["message_id"] for row in members}), "files": len(members),
                "saved": sum(row["status"] == "saved" for row in members),
                "failed": sum(row["status"] == "failed" for row in members),
                "naming_failed": sum(row["status"] == "failed" and not row["plan_json"] for row in members),
                "pending": sum(row["status"] in {"queued", "working"} for row in members),
                "paths": [row["saved_path"] for row in members if row["saved_path"]]}

    def prune(self, now: float) -> None:
        """Bound seven-day terminal metadata while retaining all archive bytes."""
        with self._connect() as database:
            database.execute("DELETE FROM members WHERE unit_id IN (SELECT id FROM units WHERE last_at<? "
                             "AND NOT EXISTS(SELECT 1 FROM members busy WHERE busy.unit_id=units.id "
                             "AND (busy.status IN ('queued','working') OR busy.updated_at>=?)))",
                             (now - 7 * 86400, now - 7 * 86400))
            database.execute("DELETE FROM units WHERE NOT EXISTS(SELECT 1 FROM members WHERE members.unit_id=units.id)")
