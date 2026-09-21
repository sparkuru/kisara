"""Tests for OneBot 11 event normalization."""

from kisara.bot.adapters.onebot_v11 import OneBotV11Adapter
from kisara.config import Settings


def _adapter() -> OneBotV11Adapter:
    """Build an adapter without opening a network connection."""

    settings = Settings(
        engine="onebot",
        instance_id="personal",
        allowed_users=frozenset(),
        groups_enabled=False,
        allowed_groups=frozenset(),
        onebot_ws_url="ws://napcat:3001",
        onebot_access_token="test-token",
    )
    return OneBotV11Adapter(settings, lambda event: None)


def test_onebot_private_event_preserves_string_identifiers() -> None:
    """Private events should expose protocol identifiers as strings."""

    event = _adapter()._to_event(
        {
            "post_type": "message",
            "message_type": "private",
            "self_id": 999,
            "user_id": 123,
            "message_id": 456,
            "message": [{"type": "text", "data": {"text": "/ping"}}],
        }
    )

    assert event is not None
    assert event.sender_id == "123"
    assert event.conversation_id == "123"
    assert event.message_id == "456"
    assert event.text == "/ping"


def test_onebot_group_event_keeps_mentions_as_segments() -> None:
    """Group conversion should preserve structured mention information."""

    event = _adapter()._to_event(
        {
            "post_type": "message",
            "message_type": "group",
            "self_id": 999,
            "user_id": 123,
            "group_id": 456,
            "message_id": 789,
            "message": [
                {"type": "at", "data": {"qq": "999"}},
                {"type": "text", "data": {"text": " hello"}},
            ],
        }
    )

    assert event is not None
    assert event.conversation_kind == "group"
    assert event.conversation_id == "456"
    assert event.segments[0].kind == "at"
    assert event.text == " hello"


def test_onebot_self_event_is_ignored() -> None:
    """The adapter must not feed its own messages into shared routing."""

    event = _adapter()._to_event(
        {
            "post_type": "message",
            "message_type": "private",
            "self_id": 999,
            "user_id": 999,
            "message_id": 1,
            "message": "loop",
        }
    )

    assert event is None
