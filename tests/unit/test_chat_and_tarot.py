"""Exercise migrated local features without a protocol connection."""

from datetime import date

import pytest

from kisara.application.services.chat import ChatPolicy, ChatResponder
from kisara.application.services.tarot import TarotReader


def test_phrasebook_sources_remain_separate_and_usable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both source styles and the old combined pool should load as shipped."""

    monkeypatch.setattr("kisara.application.services.chat.random.choice", lambda replies: replies[0])
    cute = ChatResponder(ChatPolicy(library="cute"))
    tsundere = ChatResponder(ChatPolicy(library="tsundere"))
    mixed = ChatResponder(ChatPolicy(library="mixed"))

    cute_reply = cute.reply("\u4f60", "user", force=True)
    tsundere_reply = tsundere.reply("\u4f60", "user", force=True)
    assert cute_reply and "Kisara" in cute_reply
    assert tsundere_reply and cute_reply != tsundere_reply
    assert mixed.reply("\u4f60", "user", force=True)


def test_phrasebook_respects_banned_users_and_disabled_probability() -> None:
    """A ban must take precedence over a forced reply and zero rate stays quiet."""

    responder = ChatResponder(ChatPolicy(trigger_rate=0, banned_users=frozenset({"blocked"})))

    assert responder.reply("\u4f60", "blocked", force=True) is None
    assert responder.reply("\u4f60", "allowed") is None
    assert responder.reply("\u4f60", "allowed", force=True)


def test_tarot_readings_are_stable_across_reader_instances() -> None:
    """The daily result must survive restarting the process."""

    today = lambda: date(2026, 9, 23)
    first = TarotReader(spread_rate=0, today=today)
    restarted = TarotReader(spread_rate=0, today=today)

    assert first.reading("user", "personal") == restarted.reading("user", "personal")
    assert first.reading("user", "personal") == first.reading("user", "personal", "single")
    spread = first.reading("user", "personal", "spread")
    assert len(spread.splitlines()) >= 4
