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


def test_unrequested_image_is_silent() -> None:
    """An allowed image without a recognized command should get no fallback reply."""
    dispatcher = Dispatcher(
        allowed_users=frozenset({"user-1"}),
        groups_enabled=False,
        allowed_groups=frozenset(),
    )
    original = _event(text="", message_id="image-1")
    event = MessageEvent(
        engine=original.engine, instance_id=original.instance_id,
        message_id=original.message_id, conversation_kind=original.conversation_kind,
        conversation_id=original.conversation_id, sender_id=original.sender_id,
        segments=(MessageSegment("image", {"file": "sticker.gif"}),),
        reply_context=original.reply_context,
    )
    assert dispatcher.dispatch_payload(event) is None
    for index, segment in enumerate((
        MessageSegment("mface", {"url": "https://example.com/sticker.gif"}),
        MessageSegment("file", {"file_name": "photo.png"}),
    ), 1):
        media_event = MessageEvent(
            engine=event.engine, instance_id=event.instance_id,
            message_id="media-{}".format(index),
            conversation_kind=event.conversation_kind,
            conversation_id=event.conversation_id, sender_id=event.sender_id,
            segments=(segment,), reply_context=event.reply_context,
        )
        assert dispatcher.dispatch_payload(media_event) is None
    forward = MessageEvent(
        engine=event.engine, instance_id=event.instance_id,
        message_id="forward-1", conversation_kind=event.conversation_kind,
        conversation_id=event.conversation_id, sender_id=event.sender_id,
        segments=(MessageSegment("forward", {"id": "merged"}),),
        reply_context=event.reply_context,
    )
    assert dispatcher.dispatch_payload(forward) is None


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


def test_recall_requires_quoted_bot_message_and_group_authority() -> None:
    """Only an allowed group admin may request deletion of a bot message."""

    dispatcher = Dispatcher(
        allowed_users=frozenset({"user-1"}),
        groups_enabled=True,
        allowed_groups=frozenset({"group-1"}),
    )
    event = _event(
        message_id="recall-1", text="/recall",
        conversation_kind="group", conversation_id="group-1",
        reply_context={
            "self_id": "bot-1", "quoted_message_id": "42",
            "quoted_sender_id": "bot-1", "sender_role": "member",
        },
    )
    assert dispatcher.dispatch_result(event).status == "error"

    authorized = _event(
        message_id="recall-2", text="/recall",
        conversation_kind="group", conversation_id="group-1",
        reply_context={
            "self_id": "bot-1", "quoted_message_id": "42",
            "quoted_sender_id": "bot-1", "sender_role": "admin",
        },
    )
    result = dispatcher.dispatch_payload(authorized)
    assert result is not None
    assert result.recall_message_id == "42"
