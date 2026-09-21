"""Tests for protocol-neutral message routing."""

from typing import Mapping, Optional

from kisara.bot.contracts import MessageEvent, MessageSegment
from kisara.bot.dispatcher import Dispatcher


def _event(
    message_id: str = "message-1",
    text: str = "/ping",
    conversation_kind: str = "private",
    conversation_id: str = "conversation-1",
    sender_id: str = "user-1",
    reply_context: Optional[Mapping[str, str]] = None,
) -> MessageEvent:
    """Build a compact normalized event for dispatcher tests."""

    return MessageEvent(
        engine="onebot",
        instance_id="personal",
        message_id=message_id,
        conversation_kind=conversation_kind,
        conversation_id=conversation_id,
        sender_id=sender_id,
        segments=(MessageSegment(kind="text", data={"text": text}),),
        reply_context=reply_context or {},
    )


def test_dispatcher_routes_ping_for_allowed_user() -> None:
    """Allowed private messages should use the shared ping command."""

    dispatcher = Dispatcher(
        allowed_users=frozenset({"user-1"}),
        groups_enabled=False,
        allowed_groups=frozenset(),
    )

    assert dispatcher.dispatch(_event()) == "pong"


def test_dispatcher_rejects_disallowed_user() -> None:
    """An empty or non-matching user allowlist must not trigger a reply."""

    dispatcher = Dispatcher(
        allowed_users=frozenset(),
        groups_enabled=False,
        allowed_groups=frozenset(),
    )

    assert dispatcher.dispatch(_event()) is None


def test_dispatcher_deduplicates_message_ids() -> None:
    """A repeated event from the same adapter instance should be ignored."""

    dispatcher = Dispatcher(
        allowed_users=frozenset({"user-1"}),
        groups_enabled=False,
        allowed_groups=frozenset(),
    )
    event = _event()

    assert dispatcher.dispatch(event) == "pong"
    assert dispatcher.dispatch(event) is None


def test_dispatcher_requires_group_allowlist_and_trigger() -> None:
    """Groups need an allowlist and either a command or a bot mention."""

    dispatcher = Dispatcher(
        allowed_users=frozenset({"user-1"}),
        groups_enabled=True,
        allowed_groups=frozenset({"group-1"}),
    )

    unmentioned = _event(
        message_id="message-2",
        text="hello",
        conversation_kind="group",
        conversation_id="group-1",
        reply_context={"self_id": "bot-1"},
    )
    mentioned = MessageEvent(
        engine=unmentioned.engine,
        instance_id=unmentioned.instance_id,
        message_id="message-3",
        conversation_kind=unmentioned.conversation_kind,
        conversation_id=unmentioned.conversation_id,
        sender_id=unmentioned.sender_id,
        segments=(
            MessageSegment(kind="at", data={"qq": "bot-1"}),
            MessageSegment(kind="text", data={"text": " hello"}),
        ),
        reply_context=unmentioned.reply_context,
    )

    assert dispatcher.dispatch(unmentioned) is None
    assert dispatcher.dispatch(mentioned) == "Kisara received: hello"
