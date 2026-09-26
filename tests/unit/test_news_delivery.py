"""Check durable state used by automatic daily brief delivery."""

import sqlite3
from pathlib import Path

import pytest

from kisara.infrastructure.persistence.news_delivery import NewsDeliveryStore


def test_deliveries_survive_reopening_state(tmp_path: Path) -> None:
    """A restarted bot should know which group already received a brief."""

    first = NewsDeliveryStore(str(tmp_path))
    assert not first.was_sent("2026-09-23", "group-1")
    first.mark_sent("2026-09-23", "group-1")

    restarted = NewsDeliveryStore(str(tmp_path))
    assert restarted.was_sent("2026-09-23", "group-1")
    assert not restarted.was_sent("2026-09-23", "group-2")
    assert not restarted.was_sent("2026-09-24", "group-1")


def test_private_deliveries_are_independent_and_durable(tmp_path: Path) -> None:
    """Equal QQ and group numbers retain separate, idempotent completion state."""
    store = NewsDeliveryStore(str(tmp_path))
    store.mark_sent("2026-09-27", "123")
    assert not store.was_private_sent("2026-09-27", "123")
    store.mark_private_sent("2026-09-27", "123")
    store.mark_private_sent("2026-09-27", "123")
    store.mark_sent("2026-09-27", "123")

    restarted = NewsDeliveryStore(str(tmp_path))
    assert restarted.was_sent("2026-09-27", "123")
    assert restarted.was_private_sent("2026-09-27", "123")
    assert not restarted.was_private_sent("2026-09-27", "456")
    assert not restarted.was_private_sent("2026-09-28", "123")
    with sqlite3.connect(str(tmp_path / "news_delivery.sqlite3")) as database:
        assert database.execute("SELECT COUNT(*) FROM private_deliveries").fetchone() == (1,)
        assert database.execute("SELECT COUNT(*) FROM deliveries").fetchone() == (1,)


def test_existing_group_only_database_is_upgraded_without_loss(tmp_path: Path) -> None:
    """Add the private table to an actual old schema instead of recreating state."""
    with sqlite3.connect(str(tmp_path / "news_delivery.sqlite3")) as database:
        database.execute(
            "CREATE TABLE deliveries (day TEXT NOT NULL, group_id TEXT NOT NULL, "
            "PRIMARY KEY (day, group_id))"
        )
        database.execute("INSERT INTO deliveries VALUES (?, ?)", ("2026-09-27", "123"))
        old_schema = database.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'deliveries'"
        ).fetchone()

    store = NewsDeliveryStore(str(tmp_path))
    assert store.was_sent("2026-09-27", "123")
    assert not store.was_private_sent("2026-09-27", "123")
    store.mark_private_sent("2026-09-27", "123")
    reopened = NewsDeliveryStore(str(tmp_path))
    assert reopened.was_sent("2026-09-27", "123")
    assert reopened.was_private_sent("2026-09-27", "123")
    with sqlite3.connect(str(tmp_path / "news_delivery.sqlite3")) as database:
        assert database.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'deliveries'"
        ).fetchone() == old_schema


@pytest.mark.parametrize("kind", ["group", "private"])
def test_either_completion_prunes_both_tables_at_30_day_boundary(
    tmp_path: Path, kind: str,
) -> None:
    """Keep the boundary day and clear older records of either target kind."""
    store = NewsDeliveryStore(str(tmp_path))
    for day in ("2026-08-27", "2026-08-28", "2026-09-26"):
        store.mark_sent(day, "123")
        store.mark_private_sent(day, "123")
    if kind == "group":
        store.mark_sent("2026-09-27", "456")
    else:
        store.mark_private_sent("2026-09-27", "456")
    assert not store.was_sent("2026-08-27", "123")
    assert not store.was_private_sent("2026-08-27", "123")
    assert store.was_sent("2026-08-28", "123")
    assert store.was_private_sent("2026-08-28", "123")
    assert store.was_sent("2026-09-26", "123")
    assert store.was_private_sent("2026-09-26", "123")
