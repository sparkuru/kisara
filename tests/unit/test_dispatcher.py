"""Tests for protocol-neutral message routing."""

from dataclasses import replace
from types import SimpleNamespace
from typing import Mapping, Optional

import pytest

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


def test_file_status_and_empty_events_do_not_reply() -> None:
    """Non-text events after an export must not trigger a status reply."""

    dispatcher = Dispatcher(
        allowed_users=frozenset({"user-1"}),
        groups_enabled=False,
        allowed_groups=frozenset(),
    )
    for index, segments in enumerate((
        (MessageSegment("file", {"file": "pending-upload"}),),
        (MessageSegment("reply", {"id": "quoted-image"}),),
        (MessageSegment("text", {"text": ""}),),
        (),
    )):
        event = MessageEvent(
            engine="onebot", instance_id="personal",
            message_id="empty-{}".format(index),
            conversation_kind="private", conversation_id="conversation-1",
            sender_id="user-1", segments=segments, reply_context={},
        )
        result = dispatcher.dispatch_result(event)
        assert result.status == "unhandled"
        assert result.reply is None


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


@pytest.mark.parametrize("engine", ["onebot", "local", "telegram"])
@pytest.mark.parametrize("feature,command", [("music", "/music song"), ("news", "/news")])
@pytest.mark.parametrize("configured", [None, True, False])
def test_missing_service_preserves_qq_fallback_without_enabling_handler(
        engine: str, feature: str, command: str, configured: Optional[bool]) -> None:
    """A true switch cannot manufacture a provider; only explicit false alters QQ fallback."""
    switches = {} if configured is None else {feature: configured}
    dispatcher = Dispatcher(frozenset({"user-1"}), False, frozenset(), feature_switches=switches)
    event = replace(_event(text=command), engine=engine)
    assert not dispatcher.router.eligible(feature, engine)
    result = dispatcher.dispatch_result(event)
    assert result.status == "unhandled"
    if engine == "telegram" or configured is False:
        assert result.reply == "This feature is unavailable. Try /help."
    else:
        assert result.reply == "Kisara received: " + command


def test_missing_music_preserves_non_slash_phrasebook_fallback() -> None:
    calls = []
    def reply(content: str, sender: str, **kwargs: object) -> str:
        calls.append(content)
        return "phrasebook reply"
    dispatcher = Dispatcher(frozenset({"user-1"}), False, frozenset(),
                            chat_responder=SimpleNamespace(reply=reply))
    assert dispatcher.dispatch(_event(text="music song")) == "phrasebook reply"
    assert calls == ["music song"]


@pytest.mark.parametrize("kind,groups_enabled,expected", [("private", False, True),
                                                         ("group", False, False),
                                                         ("group", True, True),
                                                         ("channel", True, False)])
def test_public_tguid_retains_group_switch_and_returns_sender(
        kind: str, groups_enabled: bool, expected: bool) -> None:
    router = Dispatcher(frozenset(), groups_enabled, frozenset(),
                        public_features={"telegram": frozenset({"tguid"})})
    event = replace(_event(text="/tguid", conversation_kind=kind, conversation_id="-456",
                           sender_id="123", reply_context={"quoted_sender_id": "999"}), engine="telegram")
    result = router.dispatch_result(event)
    assert result.status == ("handled" if expected else "unhandled")
    assert result.reply == ("123" if expected else None)
    assert router.dispatch_result(event).reply is None


def test_public_tguid_is_explicit_and_chat_scoped() -> None:
    event = replace(_event(text="/tguid", sender_id="123"), engine="telegram")
    strict = Dispatcher(frozenset(), False, frozenset())
    assert strict.dispatch(event) is None
    allowed = Dispatcher(frozenset({"123"}), False, frozenset())
    assert allowed.dispatch(event) == "123"
    router = Dispatcher(frozenset(), False, frozenset(),
                        public_features={"telegram": frozenset({"tguid"})})
    assert router.dispatch(event) == "123"
    assert router.dispatch(replace(event, conversation_id="other-chat")) == "123"
    arguments = replace(event, message_id="args", segments=(MessageSegment("text", {"text": "/tguid 999"}),))
    result = router.dispatch_result(arguments)
    assert result.status == "error" and result.reply == "Usage: /tguid"


@pytest.mark.parametrize("command", ["/tguid-other", "/tguidx", "/tguid@other", "tguid", "/ping",
                                      "/song hi", "/news", "/tgsetu on", "/unknown"])
def test_only_public_tguid_has_access(command: str) -> None:
    calls = []
    service = SimpleNamespace(music=lambda query: calls.append(query))
    news = SimpleNamespace(get=lambda: calls.append("news"))
    router = Dispatcher(frozenset(), True, frozenset(), public_services=service, daily_news=news,
                        feature_switches={"tgsetu": True},
                        public_features={"telegram": frozenset({"tguid"})})
    event = replace(_event(text=command, conversation_kind="group"), engine="telegram")
    assert router.dispatch(event) is None and not calls
    assert not router.authorize_native(event, "tgsetu")


@pytest.mark.parametrize("engine,alias", [("telegram", "/start"), ("telegram", "/ahelp"),
                                        ("onebot", "/ahelp"), ("official", "/help")])
def test_public_aliases_and_engine_isolation(engine: str, alias: str) -> None:
    router = Dispatcher(frozenset(), False, frozenset(),
                        public_features={engine: frozenset({"help"})})
    event = replace(_event(text=alias), engine=engine)
    assert "Available commands" in router.dispatch(event)
    for other in {"telegram", "onebot", "official", "local"} - {engine}:
        assert router.dispatch(replace(event, engine=other)) is None
    disabled = Dispatcher(frozenset(), False, frozenset(), feature_switches={"help": False},
                          public_features={engine: frozenset({"help"})})
    assert disabled.dispatch(event) is None


@pytest.mark.parametrize("engine,kind,expected", [("official", "channel", "pong"),
                                               ("onebot", "channel", None),
                                               ("telegram", "channel", None)])
def test_public_conversation_scope(engine: str, kind: str, expected: Optional[str]) -> None:
    router = Dispatcher(frozenset(), True, frozenset(),
                        public_features={engine: frozenset({"ping"})})
    assert router.dispatch(replace(_event(conversation_kind=kind), engine=engine)) == expected


@pytest.mark.parametrize("feature,text", [("music", "music song"), ("news", "news"),
                                        ("tarot", "tarot"), ("chat", "chat hi")])
def test_public_unassembled_features_cannot_fall_back(feature: str, text: str) -> None:
    router = Dispatcher(frozenset(), False, frozenset(),
                        public_features={"onebot": frozenset({feature})},
                        feature_switches={feature: True})
    assert router.dispatch(_event(text=text)) is None


def test_public_ping_arguments_never_trigger_phrasebook_fallback() -> None:
    calls = []
    service = SimpleNamespace(reply=lambda content, sender, **kwargs: calls.append(content) or "chat")
    router = Dispatcher(frozenset(), True, frozenset(), chat_responder=service,
                        public_features={"onebot": frozenset({"ping"})})
    assert router.dispatch(_event(text="ping hello")) == "Usage: /ping"
    assert not calls
    assert router.dispatch(_event(text="ordinary", message_id="ordinary")) is None
    assert router.dispatch(_event(text="pingpong", message_id="prefix")) is None
    assert not calls
    allowed = Dispatcher(frozenset({"user-1"}), True, frozenset(), chat_responder=service,
                         public_features={"onebot": frozenset({"ping"})})
    assert allowed.dispatch(_event(text="ping hello")) == "chat"
    assert calls == ["ping hello"]


def test_public_news_includes_maintenance_but_not_scheduling() -> None:
    calls = []
    news = SimpleNamespace(clear_cache=lambda: calls.append("clear") or True)
    router = Dispatcher(frozenset(), True, frozenset(), daily_news=news,
                        public_features={"onebot": frozenset({"news", "news_push"})})
    event = _event(text="清除新闻缓存", conversation_kind="group")
    assert router.authorize_command(event, "news")
    assert router.authorize_command(event, "news")
    assert "已清除" in router.dispatch(event)
    assert router.dispatch(event) is None
    assert not router.authorize_native(event, "news_push")
    assert calls == ["clear"]


def test_public_recall_preserves_quoted_bot_and_group_admin_rules() -> None:
    router = Dispatcher(frozenset(), True, frozenset(),
                        public_features={"onebot": frozenset({"recall"})})
    event = _event(text="/recall", conversation_kind="group", reply_context={
        "self_id": "bot", "quoted_message_id": "42", "quoted_sender_id": "other", "sender_role": "admin"})
    assert router.dispatch_result(event).status == "error"
    event = replace(event, message_id="member", reply_context={
        "self_id": "bot", "quoted_message_id": "42", "quoted_sender_id": "bot", "sender_role": "member"})
    assert router.dispatch_result(event).status == "error"
    event = replace(event, message_id="admin", reply_context={**event.reply_context, "sender_role": "admin"})
    assert router.dispatch_payload(event).recall_message_id == "42"


@pytest.mark.parametrize("feature,text", [("ping", "ping hello"), ("chat", "/chat hello"),
                                        ("source", "/source"), ("recall", "/recall")])
def test_disabled_public_feature_cannot_fall_through_for_allowed_caller(feature: str, text: str) -> None:
    """Existing allow membership cannot revive a disabled published feature."""
    calls = []
    chat = SimpleNamespace(reply=lambda *args, **kwargs: calls.append("chat"))
    services = SimpleNamespace(source_search=lambda *args: calls.append("source"))
    router = Dispatcher(frozenset({"user-1"}), False, frozenset(), chat_responder=chat,
                        public_services=services, feature_switches={feature: False},
                        public_features={"onebot": frozenset({feature})})
    event = _event(text=text, reply_context={
        "self_id": "bot", "quoted_message_id": "42", "quoted_sender_id": "bot"})
    assert not router.authorize_command(event, feature)
    result = router.dispatch_result(event)
    assert result.status == "unhandled" and result.reply == "This feature is unavailable. Try /help."
    assert not result.recall_message_id and not calls
