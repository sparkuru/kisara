"""Check durable state used by automatic daily brief delivery."""

from pathlib import Path

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
